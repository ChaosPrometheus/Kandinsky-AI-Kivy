from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
from kivy.core.image import Image as CoreImage
from io import BytesIO
import json
import time
import requests
import base64

class KandinskyAPI:
    def __init__(self, url, api_key, secret_key):
        self.URL = url
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }

    def get_model(self):
        response = requests.get(self.URL + 'key/api/v1/models', headers=self.AUTH_HEADERS)
        data = response.json()
        return data[0]['id']

    def generate(self, prompt, model, images=1, width=1024, height=1024, style=None, negative_prompt=None):
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": width,
            "height": height,
            "generateParams": {
                "query": prompt
            }
        }
        
        if style:
            params["style"] = style
        if negative_prompt:
            params["negativePromptUnclip"] = negative_prompt

        data = {
            'model_id': (None, model),
            'params': (None, json.dumps(params), 'application/json')
        }
        response = requests.post(self.URL + 'key/api/v1/text2image/run', headers=self.AUTH_HEADERS, files=data)
        data = response.json()
        return data['uuid']

    def check_generation(self, request_id, attempts=10, delay=10):
        while attempts > 0:
            response = requests.get(self.URL + 'key/api/v1/text2image/status/' + request_id, headers=self.AUTH_HEADERS)
            data = response.json()
            if data['status'] == 'DONE':
                return data['images']
            attempts -= 1
            time.sleep(delay)

    def get_styles(self):
        styles = [
            {
                "имя": "КАНДИНСКИЙ",
                "title": "Кандинский",
                "titleEn": "Кандинский",
                "изображение": "https://cdn.fusionbrain.ai/static/download/img-style-kandinsky.png"
            },
            {
                "имя": "UHD",
                "title": "Детальное фото",
                "titleEn": "Детальное фото",
                "изображение": "https://cdn.fusionbrain.ai/static/download/img-style-detail-photo.png"
            },
            {
                "имя": "АНИМЭ",
                "title": "Аниме",
                "titleEn": "Аниме",
                "изображение": "https://cdn.fusionbrain.ai/static/download/img-style-anime.png"
            },
            {
                "имя": "ПО УМОЛЧАНИЮ",
                "title": "Свой стиль",
                "titleEn": "Нет стиль",
                "изображение": "https://cdn.fusionbrain.ai/static/download/img-style-personal.png"
            }
        ]
        return styles

    def decode_image(self, image_data, output_file):
        try:
            image_bytes = base64.b64decode(image_data)
            with open(output_file, 'wb') as file:
                file.write(image_bytes)
        except Exception as e:
            print(f"ошибка {e}")

class MainApp(App):
    def build(self):
        self.api = KandinskyAPI("https://api-key.fusionbrain.ai/", "A1648E8776570B260D9DE2EFFDC38C14", "315A6E26A95F8D0908F2C3BF112DC8D4")
        self.model_id = self.api.get_model()
        
        self.layout = BoxLayout(orientation='vertical')
        
        self.prompt_input = TextInput(hint_text='Введите текст запроса', multiline=False)
        self.layout.add_widget(self.prompt_input)
        
        self.style_spinner = Spinner(
            text='Выберите стиль',
            values=[style['title'] for style in self.api.get_styles()]
        )
        self.layout.add_widget(self.style_spinner)
        
        self.width_input = TextInput(hint_text='Ширина', multiline=False)
        self.layout.add_widget(self.width_input)
        
        self.height_input = TextInput(hint_text='Высота', multiline=False)
        self.layout.add_widget(self.height_input)
        
        self.generate_button = Button(text='Создать изображение')
        self.generate_button.bind(on_press=self.generate_image)
        self.layout.add_widget(self.generate_button)
        
        self.image_widget = Image()
        self.image_widget.bind(on_touch_down=self.on_image_touch)
        self.layout.add_widget(self.image_widget)
        
        self.status_label = Label(text='Статус: ожидает ввода')
        self.layout.add_widget(self.status_label)
        
        self.generated_image_data = None
        
        return self.layout
    
    def generate_image(self, instance):
        prompt = self.prompt_input.text
        style = self.style_spinner.text
        width = int(self.width_input.text) if self.width_input.text.isdigit() else 1024
        height = int(self.height_input.text) if self.height_input.text.isdigit() else 1024
        model_id = self.model_id
        
        style_map = {style['title']: style['имя'] for style in self.api.get_styles()}
        selected_style = style_map.get(style)
        
        self.status_label.text = 'Статус: генерация изображения...'
        request_id = self.api.generate(prompt, model_id, width=width, height=height, style=selected_style)
        
        self.status_label.text = 'Статус: ожидание результата...'
        images = self.api.check_generation(request_id)
        
        if images:
            self.generated_image_data = images[0]
            image_bytes = base64.b64decode(self.generated_image_data)
            data = BytesIO(image_bytes)
            img = CoreImage(data, ext='png').texture
            self.image_widget.texture = img
            self.status_label.text = 'Статус: изображение создано'
        else:
            self.status_label.text = 'Статус: ошибка генерации'
    
    def on_image_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            if touch.is_double_tap or touch.button == 'right':
                if self.generated_image_data:
                    self.save_image()
    
    def save_image(self):
        if not self.generated_image_data:
            return
        
        output_file = 'сгенерированная_картинка.jpg'
        try:
            image_bytes = base64.b64decode(self.generated_image_data)
            with open(output_file, 'wb') as file:
                file.write(image_bytes)
            self.status_label.text = f'Статус: изображение сохранено как {output_file}'
        except Exception as e:
            self.status_label.text = f'Статус: ошибка сохранения изображения: {e}'

if __name__ == '__main__':
    MainApp().run()
