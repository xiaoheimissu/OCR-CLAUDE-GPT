import re
from dependencies.chat import *
def split_string(text, min_length=14000, max_length=18000, numbered_headings=True):
    if numbered_headings:
        # 匹配带编号的标题 (如 # 1. 标题 或 ## 2.3 标题)
        heading_pattern = re.compile(r'^(#+\s+\d+(\.\d+)*\.?\s+.*)', re.MULTILINE)
    else:
        # 匹配所有标题 (如 # 标题 或 ## 标题)
        heading_pattern = re.compile(r'^(#+\s+.*)', re.MULTILINE)
    
    headings = [(m.start(), m.group(1)) for m in heading_pattern.finditer(text)]
    
    # 如果没有匹配到标题，直接返回整个文本
    if not headings:
        return [text]

    segments = []
    
    if headings[0][0] > 0:
        segments.append(text[:headings[0][0]])

    for i in range(len(headings)):
        start_pos = headings[i][0]
        end_pos = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        segments.append(text[start_pos:end_pos])
    
    # 合并段落，确保每段的长度在 min_length 和 max_length 之间
    result = []
    current_segment = ""
    
    def add_segment(segment):
        nonlocal current_segment
        if len(current_segment) + len(segment) > max_length:
            result.append(current_segment)
            current_segment = segment
        else:
            current_segment += segment
    
    for segment in segments:
        if len(current_segment) + len(segment) < min_length:
            current_segment += segment
        else:
            add_segment(segment)
    
    if current_segment:
        result.append(current_segment)
    
    return result



class Translator:
    def __init__(self, translation_model, polishing_model, api_key, baseurl, temperature=0.7, top_p=1, stream=False, max_retries_translater=4):
        """
        初始化 Translator 类
        :param translation_model: 翻译使用的模型名称
        :param polishing_model: 润色使用的模型名称
        :param api_key: API 密钥
        :param baseurl: API 基础 URL
        :param temperature: 生成文本的随机性
        :param top_p: 控制生成文本的多样性
        :param stream: 是否启用流式传输
        """
        self.translation_chat = Chat_Retry(api_key=api_key, model=translation_model, baseurl=baseurl, temperature=temperature, top_p=top_p, stream=stream,max_retries=max_retries_translater)
        self.polishing_chat = Chat_Retry(api_key=api_key, model=polishing_model, baseurl=baseurl, temperature=temperature, top_p=top_p, stream=stream,max_retries=max_retries_translater)

    def translate(self, texts, translation_prompt=None, polish=False, polishing_prompt=None):
        """
        对文本数组进行翻译，并根据需要进行润色
        :param texts: 需要翻译的字符串数组
        :param polish: 是否需要润色
        :param translation_prompt: 可选的自定义翻译提示语
        :param polishing_prompt: 可选的自定义润色提示语
        :return: 翻译后的文本数组（如果需要润色，则返回润色后的结果）
        """
        translated_texts = []
        
        # Step 1: 翻译每个文本
        for text in texts:
            # 使用自定义翻译提示语，如果没有提供则使用默认提示语，并附加需要翻译的内容
            prompt = f"{translation_prompt}\n{text}" if translation_prompt else f"请翻译以下内容:\n{text}"
            translated_text = self.translation_chat(prompt)
            translated_texts.append(translated_text)

        # Step 2: 如果需要润色，调用润色模型，将原始文本和翻译后的文本一起发送给润色模型
        if polish:
            polished_texts = []
            for original_text, translated_text in zip(texts, translated_texts):
                prompt = f"{polishing_prompt}\n原文：{original_text}\n翻译：{translated_text}" if polishing_prompt else f"请根据以下原文对翻译后的文本进行润色：\n原文：{original_text}\n翻译：{translated_text}"
                polished_text = self.polishing_chat(prompt)
                polished_texts.append(polished_text)
            return polished_texts

        return translated_texts


if __name__ == "__main__":
    with open('test.txt', 'r', encoding='utf-8') as file:
        content = file.read() 
    cleaned_text = split_string(content)
    
    with open('withoutspace1.txt', 'w', encoding='utf-8') as file:
        # 将所有分段写入文件
        for i, segment in enumerate(cleaned_text):
            file.write(f"--- Segment {i+1} ---\n")
            file.write(segment)
            file.write("\n\n\n\n\n\n\n\n\n\n")
