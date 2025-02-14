import cv2

from threading import Thread

from src.libs.communicator import *
from src.libs.user_interface import *
from src.libs.gesture_recognizer import *

from src.utils import (
    calculate,
    save_image,
    ip_address,
    video_capture,
    draw_landmarks,
    create
)

from src.constants import (
    Path,
    MAX_IMAGES,
    DATASETS_PATH,
    DEFAULT_GESTURE
)

class App:
    def __reset_window(self):
        self.current_window.window.destroy()
        self.current_window.create()

    def __set_window(self, index=None, *args):
        if index is not None:
            self.current_window = self.windows[index]
            self.current_window.create(*args)
        else:
            if self.current_window:
                 self.current_window.window.destroy()
                 self.current_window = None

    def __reset_video_capture(self):
        self.video_capture.stop()
        cv2.destroyAllWindows()

    def __set_video_capture(self, callback, use_thread=True):
        if not self.video_capture.is_running():
            if use_thread:
                self.video_capture_thread = Thread(
                    target=lambda: self.video_capture.start(callback)
                )

                self.video_capture_thread.start()
            else:
                self.video_capture.start(callback)

    def __reset_communication(self):
        self.communicator.stop()

    def __set_communicator(self):
        if not self.communicator.is_running():
            self.communicator_thread = Thread(
                target=self.communicator.start
            )

            self.communicator_thread.start()

    def __get_hands(self, image):
        # process 'image: ndarray' to check for 'hand(s)'
        processed_image = self.hand_detector.process(image)

        # get 'multi_hand_landmarks'
        self.multi_hand_landmarks = processed_image.multi_hand_landmarks

        # return 'multi_hand_landmarks'
        return self.multi_hand_landmarks

    def __process_recognition(self, image):
        # clone 'image: ndarray'
        new_image = image.__copy__()

        # check for 'multi_hand_landmarks' in 'ndarray'
        if self.__get_hands(new_image):
            # calculate 'frame timestamp ms: int'
            frame_timestamp_ms = calculate.frame_timestamp(self.video_capture.capture)

            # process 'new_image: ndarray' to get recognition results
            self.gesture_recognizer.process(
                image=new_image,
                frame_timestamp_ms=frame_timestamp_ms
            )

    def __process_saving(self, image):
        if self._count == (MAX_IMAGES + 1):
            self.__reset_video_capture()
            self.create.box(0, 'Информация', 'Жест успешно сохранён')
            return

        result = self.__get_hands(image)

        if result:
            self._count += 1

            save_image.save(
                image=image,
                name=self._name,
                index=self._count
            )

        draw_landmarks.draw(image, result)
        cv2.imshow('tk', image)

    def __on_gesture_received(self, gesture: str):
        if gesture != DEFAULT_GESTURE:
            for data in self.registry.get_devices():
                command = None

                for line in data[3:]:
                    key, value = line.split('=')

                    if value == gesture:
                        command = key
                        break

                if command:
                    address = (data[0], int(data[1]))

                    self.communicator.send(
                        address=address,
                        command=command
                    )

    def __on_server_received(self, data, address):
        if not self.registry.get_device(address):
            self.create.box(0, 'Уведомление', 'Новое умное устройство было обнаружено!')

            self.registry.write_device(address, data)
            self.communicator.send(address, 'ps')

    def __change(self, index=None, process=True, *args):
        self.__set_window(None)

        print(process)

        if process:
            self.__set_video_capture(self.__process_recognition)
        else:
            self.__reset_video_capture()

        self.__set_window(index, *args)

    def __on_save_gesture_pressed(self, name: str):
        if len(name) == 0:
            self.create.box(1, 'Предупреждение', 'Поле ввода не должно быть пустым!')
            return

        if len(name) < 3:
            self.create.box(1, 'Предупреждение', 'В имени должно присутствовать минимум 3 символа!')
            return

        if len(name) > 20:
            self.create.box(1, 'Предупреждение', 'В имени не должно присутствовать более 20 символов!')
            return

        if not name.isalpha():
            self.create.box(1, 'Предупреждение', 'В имени должны присутствовать только буквы из алфавита!')
            return

        gesture_path = Path.get_path_to(name, DATASETS_PATH)

        if Path.exists(gesture_path):
            self.create.box(1, 'Предупреждение', 'Имя уже занято!')
            return

        self.__set_window()

        self.create.box(0, 'Информация', '''
        Следуйте указаниям ниже:
        
         1. Включите свет в помещении
         
         2. Держите руку напротив обьектива камеры
         
         3. Не меняйте жест руки
        ''')

        Path.create_directory(gesture_path)

        self._count = 0
        self._name = name

        self.__reset_video_capture()
        self.__set_video_capture(self.__process_saving, False)

        self.__change(1, False)

    def __on_remove_gesture_pressed(self, name: str):
        box = self.create.box(2, 'Предупреждение', 'Вы уверены, что хотите удалить жест?')

        if box:
            gesture_path = Path.get_path_to(name, DATASETS_PATH)

            Path.remove_directory(gesture_path)

            self.__reset_window()

    def __init__(self):
        self.registry = Registry()
        self.communicator = Communicator(self.__on_server_received)

        self.gesture_recognizer = GestureRecognizer(self.__on_gesture_received)
        self.model_trainer = ModelTrainer()
        self.hand_detector = HandDetector()

        self.create = create.Create()
        self.video_capture = video_capture.VideoCapture()

        self.current_window = None

        self.windows = [
            Menu(self.__change),
            GesturesManager(self.__change, self.__on_remove_gesture_pressed),
            DevicesManager(self.__change),
            GestureName(self.__change, self.__on_save_gesture_pressed)
        ]

        self.__set_communicator()
        self.__set_video_capture(self.__process_recognition)

        self.create.box(0, 'Информация', f'IP-адрес станции: {ip_address.get()}')
        self.__change(0)

if __name__ == "__main__":
    App()