from camera_stuff import camera
import requests 

class AgentController:
    def __init__(self):
        self.camera = camera.Camera()

    def workflow(self):
        IMG = self.take_picture()
        response = self.send_picture(image)
        if response:
            return "continue"
        else:
            return "reading"
    
    def take_picture(self):
        result_image = None
        return result_image

    def send_picture(self, image):
        response = None
        return response
    