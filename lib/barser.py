from lib.barameters import Barameters
from multiprocessing import Process, Pipe, connection
from typing import Any, Dict, List, Optional, Tuple
from lib.bicturetaker import Bicturetaker
import time
import cv2


class BarserMethod:
    """
    the @barser decorator wraps the functions into this class.
    The barser then loops over all members of a BameInstance, looking for fields of this type.
    """
    def __init__(self, fun) -> None:
        self.fun = fun
        pass

    def run(self, *, undistorted_image, parsed_data, barser_context):
        self.fun(undistorted_image, parsed_data, barser_context)

# Decorators while pickling is broken on windows :(
# def barser(fun):
    # """
    # Decorator applied to methods to mark them as BarserMethods.
    # """
    # return BarserMethod(fun)
 
class WorkerPayload:
    """
    The actual payload which is sent from the barser to the main Bame Thread.

    This is created inside of "barser_worker(...)"

    Fields:
        image: Undistorted image
        raw_image: Raw image from the camera
        barsed_info (dict): Result which was generated from the Barsers - containing information about the game field.
    """
    def __init__(self, raw_image, image, barsed_info):
        self.raw_image = raw_image
        self.image = image
        self.barsed_info = barsed_info

class BarserOptions:
    camera_index: int
    def __init__(self) -> None:
        pass

    @staticmethod
    def from_barameters(barameters: Barameters) -> "BarserOptions":
        # TODO: Make this responsive! (barameters.add_update_handler(...))
        options = BarserOptions()
        options.camera_index = barameters.camera_index
        return options

class BarserContext:
    __dict__: Dict[str, Any]
    def __init__(self, **kwargs) -> None:
        self.__dict__ = kwargs
    def __getattr__(self, name: str) -> Any:
        return self.__dict__[name]
    def __getstate__(self):
        return self.__dict__
    def __setstate__(self, d):
        self.__dict__ = d

class BarserWorkerArguments:
    """
    Exists to catch type errors when calling Process(... barser_worker) early.
    """
    def __init__(self, *, pipe_connection: connection.Connection, barser_methods: List[BarserMethod], barser_context: BarserContext, options: BarserOptions):
        self.pipe_connection = pipe_connection
        self.barser_methods = barser_methods
        self.barser_context = barser_context
        self.options = options


def barser_worker(arguments: BarserWorkerArguments):
    """
    Worker method which runs in a seperate process. This creates the `WorkerBayload` and sends it to the `Barser`

    Workflow:
        Bicturetaker takes and processes image 
          |
          V
        Barsers are run and create the game field which will be stored in barsed_info
          |
          V
        WorkerBayload is constructed and sent over the pipe
    """
    running = True

    taker = Bicturetaker(cam_index=arguments.options.camera_index, tag_timeout=1)

    print("[BW] Worker started...")
    while running:
        if arguments.pipe_connection.poll(0):
            res = arguments.pipe_connection.recv()
            if res:
                running = False

        if running:
            d = taker.take_bicture()
            image = d["img"] if "img" in d else None
            barsed_info = None
            if image is not None:
                # cv2.imshow("DBG", image)
                # cv2.waitKey(1)
                barsed_info = {}
                for method in arguments.barser_methods:
                    method.run(
                            undistorted_image=d["img"],
                            parsed_data=barsed_info,
                            barser_context=arguments.barser_context
                            )
                #Todo. This blocks until someone reads. maybe change that behaviour. Maybe a Queue would be a better option here.
                arguments.pipe_connection.send(WorkerPayload(raw_image=d["raw"], image=image, barsed_info=barsed_info))

    print("[BW] Worker closing...")
    arguments.pipe_connection.close()

class WorkerHandle:
    """
    Unified access to the worker process.

    This class does all the multiprocessing magic.
    """
    def __init__(self, barser_methods: List[BarserMethod], barser_context: BarserContext, options: BarserOptions):

        pipe_connection, child_pipe = Pipe()
        process = Process(target=barser_worker, args=(BarserWorkerArguments(pipe_connection=child_pipe, barser_methods=barser_methods, barser_context=barser_context, options=options), ))
        process.start()

        self.pipe_connection = pipe_connection
        self.process = process

    def stop(self):
        print("Stopping worker")
        self.pipe_connection.send(True)

        # Read images which remain...
        print("Waiting for thread to shut down.")
        while True:
            try:
                self.pipe_connection.recv()
            except EOFError:
                break


        self.process.join(1)
        if self.process.is_alive():
            print("process.join(1) did not succeed.")
        self.process.close()

class BarsedWithTime:
    data: WorkerPayload
    time: float

class Barser:
    """
    Utility class to spawn a seperate process which then runs the bicture-taking and barsing
    """

    handle: Optional[WorkerHandle]
    last_barsed: Optional[BarsedWithTime]
    barser_methods: List[BarserMethod]
    def __init__(self, game_instance, *, options: BarserOptions):
        self.handle = None
        self.last_barsed = None
        self.options = options
        self.barser_context = None

        # Find all properties of type BarserMethod in the game_instance. 
        # Methods marked with @barser are also turned into BarserMethods
        self.barser_methods = []
        for m in dir(game_instance):
            val = getattr(game_instance, m)
            if isinstance(val, BarserMethod):
                self.barser_methods.append(val)
            if isinstance(val, BarserContext):
                self.barser_context = val
        

    def launch(self):
        """
        Actually launches the thread. Do not forget to call stop() at the end.
        """
        self.handle = WorkerHandle(self.barser_methods, self.barser_context, options=self.options)
        pass

    def get_bayload(self) -> Optional[BarsedWithTime]:
        """
        Last workload sent by the worker process. None if None was received yet.
        """
        assert self.handle is not None
        
        data: Optional[WorkerPayload] = None
        while self.handle.pipe_connection.poll(0):
            data = self.handle.pipe_connection.recv()

        if data is not None:
            bwt = BarsedWithTime()
            bwt.data = data
            bwt.time = time.time()
            self.last_barsed = bwt
        return self.last_barsed

    def stop(self):
        """
        Blocks until the worker process terminated.
        """
        assert self.handle is not None
        self.handle.stop()

