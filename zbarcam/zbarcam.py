import os

import PIL
import zbarlight
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ListProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.utils import platform

# Pillow is not currently available for Android:
# https://github.com/kivy/python-for-android/pull/786
try:
    # Pillow
    PIL.Image.frombytes
    PIL.Image.Image.tobytes
except AttributeError:
    # PIL
    PIL.Image.frombytes = PIL.Image.frombuffer
    PIL.Image.Image.tobytes = PIL.Image.Image.tostring

MODULE_DIRECTORY = os.path.dirname(os.path.realpath(__file__))


class ZBarCam(AnchorLayout):
    """
    Widget that use the Camera and zbar to detect qrcode.
    When found, the `codes` will be updated.
    """
    resolution = ListProperty([640, 480])

    codes = ListProperty([])
    # checking all possible types by default
    code_types = ListProperty(zbarlight.Symbologies.keys())

    # TODO: handle code types
    def __init__(self, **kwargs):
        # lazy loading the kv file rather than loading at module level,
        # that way the `XCamera` import doesn't happen too early
        Builder.load_file(os.path.join(MODULE_DIRECTORY, "zbarcam.kv"))
        super(ZBarCam, self).__init__(**kwargs)
        Clock.schedule_once(lambda dt: self._setup())

    def _setup(self):
        """
        Postpones some setup tasks that require self.ids dictionary.
        """
        if platform == 'android':
            from android.permissions import request_permission, Permission
            request_permission(Permission.CAMERA)
        self._remove_shoot_button()
        self._enable_android_autofocus()
        self.xcamera._camera.bind(on_texture=self._on_texture)
        # self.add_widget(self.xcamera)

    def _remove_shoot_button(self):
        """
        Removes the "shoot button", see:
        https://github.com/kivy-garden/garden.xcamera/pull/3
        """
        xcamera = self.xcamera
        shoot_button = xcamera.children[0]
        xcamera.remove_widget(shoot_button)

    def _enable_android_autofocus(self):
        """
        Enables autofocus on Android.
        """
        if not self.is_android():
            return
        camera = self.xcamera._camera._android_camera
        params = camera.getParameters()
        params.setFocusMode('continuous-video')
        camera.setParameters(params)

    def _on_texture(self, instance):
        self.codes = self._detect_qrcode_frame(
            texture=instance.texture, code_types=self.code_types)

    @staticmethod
    def _detect_qrcode_frame(texture, code_types):
        image_data = texture.pixels
        size = texture.size
        fmt = texture.colorfmt.upper()
        # PIL doesn't support BGRA but IOS uses BGRA for the camera
        # if BGRA is detected it will switch to RGBA, color will be off
        # but we don't care as it's just looking for barcodes
        if platform == 'ios' and fmt == 'BGRA':
            fmt = 'RGBA'
        pil_image = PIL.Image.frombytes(mode=fmt, size=size, data=image_data)
        return zbarlight.scan_codes(code_types, pil_image) or []

    @property
    def xcamera(self):
        return self.ids['xcamera']

    def start(self):
        self.xcamera.play = True

    def stop(self):
        self.xcamera.play = False

    def is_android(self):
        return platform == 'android'


DEMO_APP_KV_LANG = """
BoxLayout:
    orientation: 'vertical'
    ZBarCam:
        id: zbarcam
        code_types: 'qrcode', 'ean13'
    Label:
        size_hint: None, None
        size: self.texture_size[0], 50
        text: ', '.join([str(code) for code in zbarcam.codes])
"""


class DemoApp(App):

    def build(self):
        return Builder.load_string(DEMO_APP_KV_LANG)


if __name__ == '__main__':
    DemoApp().run()
