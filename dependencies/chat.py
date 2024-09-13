import requests
import time

class Chat:
    def __init__(self, api_key=None, model=None, baseurl=None, temperature=0.7, top_p=1, stream=False):
        """
        初始化 ChatGPT 类并设置默认参数。
        :param api_key: API 密钥
        :param model: 模型名称
        :param baseurl: API 基础 URL
        :param temperature: 生成文本的随机性
        :param top_p: 控制生成文本的多样性
        :param stream: 是否启用流式传输
        """
        self.api_key = api_key
        self.model = model
        self.baseurl = baseurl
        self.temperature = temperature
        self.top_p = top_p
        self.stream = stream  

    def send_request(self, prompt, img_url=None, api_key=None, model=None, baseurl=None, temperature=None, top_p=None, stream=None):
        """
        :param prompt: 用户输入的文本提示 string
        :param img_url: 可选的图片 URL
        :return: API 返回的响应文本
        """
        # 使用传入的参数或默认值
        api_key = api_key or self.api_key
        model = model or self.model
        baseurl = baseurl or self.baseurl
        temperature = temperature if temperature is not None else self.temperature
        top_p = top_p if top_p is not None else self.top_p
        stream = stream if stream is not None else self.stream  

        if not api_key or not model or not baseurl:
            raise ValueError("API key, model, and baseurl are required.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = [{"role": 'user', "content": prompt}]  

        # 如果有 img_url，则添加图片内容
        if img_url:
            messages[0]['content'] = [
                {"type": "image_url", "image_url": {"url": img_url}},
                {"type": "text", "text": prompt}
            ]

        data = {
            "model": model,
            "stream": stream,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p
        }

        try:
            # 发送请求
            response = requests.post(baseurl, headers=headers, json=data)
            response.raise_for_status()  
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            # print(f"HTTPError: {e}")
            # print(f"Response content: {response.text}")
            raise e

    def __call__(self, prompt, img_url=None, api_key=None, model=None, baseurl=None, temperature=None, top_p=None, stream=None):
        return self.send_request(prompt, img_url, api_key, model, baseurl, temperature, top_p, stream)


class Chat_Retry(Chat):
    def __init__(self, api_key=None, model=None, baseurl=None, temperature=0.7, top_p=1, stream=False, max_retries=3, retry_delay=2):
        """
        初始化 ChatGPT_Retry 类，增加重试机制。
        :param max_retries: 最大重试次数
        :param retry_delay: 每次重试之间的延迟时间（秒）
        """
        super().__init__(api_key, model, baseurl, temperature, top_p, stream)  
        self.max_retries = max_retries  # 设置最大重试次数
        self.retry_delay = retry_delay  # 设置重试间隔时间

    def send_request(self, prompt, img_url=None, api_key=None, model=None, baseurl=None, temperature=None, top_p=None, stream=None):
        """
        重写父类的 send_request 方法，增加重试机制。
        """
        for attempt in range(self.max_retries):
            try:
                return super().send_request(prompt, img_url, api_key, model, baseurl, temperature, top_p, stream)
            except requests.exceptions.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)  
                else:
                    raise Exception(f"Max retries exceeded. Last error: {e}")



def ocr_with_chatgpt(prompt, image_url, chat_instance, ocr_max_retries=5):
    for attempt in range(ocr_max_retries):
        try:
            return chat_instance(prompt, img_url=image_url)
        except Exception as e:
            if attempt < ocr_max_retries - 1:
                print(f"OCR attempt ({attempt + 1} / {ocr_max_retries}) failed for {image_url}. Retrying...")
                time.sleep(3)
            else:
                return f"OCR failed for {image_url}: {e}"