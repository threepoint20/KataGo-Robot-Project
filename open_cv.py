import cv2
import sys
import numpy as np # Import numpy for array operations and pi constant

# --- Main Program ---
if __name__ == "__main__":
    # Confirmed Camo Camera is at index 0 on your system
    cam_index = 0 

    print(f"嘗試打開攝影機索引: {cam_index}")
    cap = cv2.VideoCapture(cam_index)

    # Set camera resolution (adjust as needed, 720p is a good starting point)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print(f"錯誤：無法打開攝影機索引 {cam_index}。請確認 Camo Camera 應用程式正常運作並連接。")
        sys.exit("程式終止。")

    print("成功連接到 Camo Camera。按 'q' 鍵退出視窗。")

    while True:
        ret, frame = cap.read() # Read a frame (BGR color image)
        if not ret:
            print("無法從攝影機讀取影像串流，可能已斷開連接或無效幀。")
            break

        # --- Image Preprocessing ---
        
        # 1. Convert to Grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 2. Gaussian Blur to reduce noise and smooth the image
        # (5, 5) is the kernel size (must be odd), 0 is sigmaX (auto calculated)
        blurred_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)
        
        # 3. Canny Edge Detection to find strong edges
        # Adjust min_val and max_val (e.g., 50, 150 or 100, 200) based on your lighting and clarity
        edges = cv2.Canny(blurred_frame, 100, 200) # You might need to tune these thresholds


        # --- Line Detection using Probabilistic Hough Transform ---
        
        # Parameters for HoughLinesP (Probabilistic Hough Line Transform)
        # These parameters are crucial and often require tuning based on your image.
        rho = 1             # Distance resolution of the accumulator in pixels
        theta = np.pi / 180  # Angle resolution of the accumulator in radians (1 degree)
        threshold = 15      # Accumulator threshold parameter. Only lines with enough votes are returned.
                            # Increase to detect fewer, stronger lines. Decrease to detect more, weaker lines.
        min_line_length = 50 # Minimum line length. Lines shorter than this are rejected.
        max_line_gap = 20    # Maximum allowed gap between points on the same line to link them.
                            # Increase to connect broken lines.

        lines = cv2.HoughLinesP(edges, rho, theta, threshold, minLineLength=min_line_length, maxLineGap=max_line_gap)

        # --- Visualization ---
        
        # Create a copy of the original frame to draw lines on
        line_detection_frame = frame.copy() 
        
        # Draw detected lines on the copy
        if lines is not None:
            for line in lines:
                # lines will be a NumPy array of shape (N, 1, 4), where N is the number of lines
                # Each line is [x1, y1, x2, y2]
                x1, y1, x2, y2 = line[0] # Access the 4 coordinates from the inner array
                cv2.line(line_detection_frame, (x1, y1), (x2, y2), (0, 0, 255), 2) # Draw in Red (BGR), thickness 2

        # --- Display Windows ---
        cv2.imshow('Original Color Frame', frame)
        cv2.imshow('Grayscale Frame', gray_frame)
        cv2.imshow('Blurred Frame', blurred_frame)
        cv2.imshow('Canny Edges', edges)
        cv2.imshow('Hough Lines', line_detection_frame) # Display the frame with detected lines


        # --- Exit Condition ---
        # Press 'q' to quit the loop and close windows
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # --- Release Resources ---
    cap.release()
    cv2.destroyAllWindows()
    print("程式正常退出。")