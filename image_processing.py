# from xml.etree.ElementTree import tostring
from PIL import Image
import pytesseract
from pytesseract import Output
import imutils
import cv2
# from ctypes import resize
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import interpolation as inter

# The final variant of code
### Function declaration
# Calculate skew angle of an image
def getSkewAngle(contour) -> int:
    largestContour = contour
    minAreaRect = cv2.minAreaRect(largestContour)

    # Determine the angle. Convert it to the value that was originally used to obtain skewed image
    angle = minAreaRect[-1]
    if angle < -45:
        print("Angle =", angle)
        angle = 90 + angle
    return -1.0 * angle


def correct_skew(image, delta=1, limit=5):
    def determine_score(arr, angle):
        data = inter.rotate(arr, angle, reshape=False, order=0)
        histogram = np.sum(data, axis=1, dtype=float)
        score = np.sum((histogram[1:] - histogram[:-1]) ** 2, dtype=float)
        return histogram, score

    thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1] 

    scores = []
    angles = np.arange(-limit, limit + delta, delta)
    for angle in angles:
        histogram, score = determine_score(thresh, angle)
        scores.append(score)

    best_angle = angles[scores.index(max(scores))]

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, best_angle, 1.0)
    corrected = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, \
            borderMode=cv2.BORDER_REPLICATE)

    return best_angle, corrected

# pytesseract.pytesseract.tesseract_cmd = r'<C:/Program Files/Tesseract-OCR/tesseract.exe>'
img_path = "img/test.jpg";
img = cv2.imread(img_path, cv2.IMREAD_COLOR)

### Resize image
# img = cv2.resize(img, (720, 576)) # 620 x 480
# img = cv2.resize(img, (620, 480))

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # convert to grey scale
gray = cv2.bilateralFilter(gray, 11, 17, 17)  # Blur to reduce noise
edged = cv2.Canny(gray, 30, 200)  # Perform Edge detection

# find contours in the edged image, keep only the largest
# ones, and initialize our screen contour
cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)
cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]
largestCnt = cnts[0]
screenCnt = None

# loop over our contours
for c in cnts:
    # approximate the contour
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.018 * peri, True)

    # if our approximated contour has four points, then
    # we can assume that we have found our screen
    if len(approx) == 4:
      screenCnt = approx
      break

if screenCnt is None:
    detected = 0
    print("No contour detected")
else:
    detected = 1

if detected == 1:
    cv2.drawContours(img, [screenCnt], -1, (0, 255, 0), 3)


# Masking the part other than the number plate
mask = np.zeros(gray.shape, np.uint8)
new_image = cv2.drawContours(mask, [screenCnt], 0, 255, -1,)
new_image = cv2.bitwise_and(img, img, mask=mask)

# Now crop
(x, y) = np.where(mask == 255)
(topx, topy) = (np.min(x), np.min(y))
(bottomx, bottomy) = (np.max(x), np.max(y))
Cropped = gray[topx:bottomx+1, topy:bottomy+1]


negate = True
threshold = True 
erode = True
corect_rotation = True

if negate:
    Cropped = cv2.bitwise_not(Cropped);

if threshold: 
    _,Cropped = cv2.threshold(Cropped,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    # Cropped =  cv2.adaptiveThreshold(Cropped,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, \
    #             cv2.THRESH_BINARY, 57, 3)

if erode:
    Cropped = cv2.erode(Cropped, (2, 2), iterations=2)

if corect_rotation:
    angle, Cropped = correct_skew(Cropped)
    # print("New angle:", angle)

license_number = ""

with open("results.txt", "a") as file: 
    print("Is file writable: ", file.writable())
    file.write("\n\n------------------------------\n")
    file.write("|Image name: " + img_path[4:])
    file.write("\n|Applied transformations:\n" + "|\timg_negate: " + str(negate) + "\n"
                + "|\tthreshold_otsu: " + str(threshold) + "\n"
                + "|\terode: " + str(erode) + "\n"
                + "|\tskew_correction: " + str(corect_rotation)
                + "\n------------------------------")

    for i in range(6, 14):
        personal_config = rf"--psm {i}  tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz --oem 3"
        data = pytesseract.image_to_data(
            Cropped, config=personal_config, output_type=Output.DICT)
        
        output_string = "\npsm = " + str(i);
        file.write(output_string)
        for elem in range(len(data['text'])):
            if data['conf'][elem] > 0:
                output_string = "\n'" + data['text'][elem] + "' = " + str(data['conf'][elem]) + "%"
                file.write(output_string)
                if data['text'][elem].isupper() and data['text'][elem].isalpha() or data['text'][elem].isnumeric(): 
                    license_number = license_number + data['text'][elem] + " "

                if i == 6: 
                    license_number = data['text'][elem] if len(data['text'][elem]) >= 2 else ""

        file.write("\nLicense number: " + license_number)
        license_number = ""
        file.write("\n") 

    file.write("____________________________")
file.close();

# cv2.imshow('originam image', img)
# cv2.imshow('cropped image', Cropped)

# cv2.waitKey(0)
# cv2.destroyAllWindows()
