LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


def extract_eye_landmarks(face_landmarks, frame_w, frame_h):

    left_eye = []
    right_eye = []

    for idx in LEFT_EYE:
        lm = face_landmarks.landmark[idx]
        left_eye.append((int(lm.x * frame_w), int(lm.y * frame_h)))

    for idx in RIGHT_EYE:
        lm = face_landmarks.landmark[idx]
        right_eye.append((int(lm.x * frame_w), int(lm.y * frame_h)))

    return left_eye, right_eye