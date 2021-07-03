import cv2
from pupil_apriltags import Detector
import numpy as np

class Bicturetaker:

    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 1920)
        self.cap.set(4, 1080)
        self.detector = Detector(families='tag16h5',
                        nthreads=8,
                        quad_decimate=1.0,
                        quad_sigma=0.0,
                        refine_edges=1,
                        decode_sharpening=0.25,
                        debug=0)
        self.last_results = None

    def take_bicture(self):
        _, img = self.cap.read()
        gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)

        results = []
        if self.last_results:
            for last_result in self.last_results:
                x1 = int(min([x for (x, _) in last_result.corners])) - 10
                x1 = x1 if x1 >= 0 else 0
                x2 = int(max([x for (x, _) in last_result.corners])) + 10
                x2 = x2 if x1 < img.shape[1] else img.shape[1]
                y1 = int(min([y for (_, y) in last_result.corners])) - 10
                y1 = y1 if y1 >= 0 else 0
                y2 = int(max([y for (_, y) in last_result.corners])) + 10
                y2 = y2 if y2 < img.shape[0] else img.shape[0]
                cv2.line(img, (x1, y1), (x1, y2), (255, 0, 0))
                cv2.line(img, (x1, y2), (x2, y2), (255, 0, 0))
                cv2.line(img, (x2, y2), (x2, y1), (255, 0, 0))
                cv2.line(img, (x2, y1), (x1, y1), (255, 0, 0))
                res = self.detector.detect(gray[y1:y2,x1:x2])
                if len(res) != 1:
                    break
                for i in range(4):
                    res[0].corners[i] += (x1, y1)
                results.append(res[0])
        if len(results) != 4:
            results = self.detector.detect(gray)

        results = [result for result in results if result.tag_id in range(4)]

        if len(results) == 4:
            actual = np.zeros([4, 2], dtype=np.float32)
            for result in results:
                print(result)
                id = result.tag_id
                if actual[id][0] != 0 or actual[id][1]:
                    return None
                actual[id] = result.corners[id]

            self.last_results = results

            target = np.float32([
                [0.0, img.shape[0]],
                [img.shape[1], img.shape[0]],
                [img.shape[1], 0.0],
                [0.0, 0.0]
            ])
            print(actual)
            print(target)
            matrix = cv2.getPerspectiveTransform(actual, target)
            distorted = cv2.warpPerspective(img, matrix, (img.shape[1], img.shape[0]))

            return distorted
        
        last_result = None
        return None


def main():
    bt = Bicturetaker()
    while True:
        img = bt.take_bicture()

        if img is not None:
            img = cv2.resize(img, (960, 540))
            cv2.imshow("Image: ", img)
            key = cv2.waitKey(1)
            if key == 27:
                return

if __name__ == '__main__':
    main()
