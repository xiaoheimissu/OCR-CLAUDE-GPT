import concurrent.futures
from dependencies.chat import *
from dependencies.text_translater import *




FILE_TO_TRANSLATER = "256-287.txt"
FILE_SAVE = "256-287_trans.txt"
API_KEY = "hk-**********************"
BASEURL = "https://**************/v1/chat/completions"
TRANSLATER_MODEL = "chatgpt-4o-latest"  
POLISHING_MODEL = "claude-3-5-sonnet-20240620"  

TRANSLATE_PROMPT =      """扮演翻译官的角色, 我需要你将英文内容翻译成中文, 以下是回复要求:
                           1. 保持原意, 确保语言流畅且具有学术性. 请特别注意专业术语的准确翻译. 翻译后文本的读者是中文母语学者. 
                           2. 你的回复应当简洁明了, 仅包含翻译内容, 不要添加任何额外解释, 即使要翻译的内容为空. 请不要回复任何不在原文翻译中的内容.
                        """

POLISHING_PROMPT =      """担任翻译润色的角色, 通过对比翻译前后的内容进行润色, 以下是回复要求:
                           1. 确保翻译内容的准确性及专业术语的正确使用.
                           2. 文本中的Markdown格式可能不正确, 请进行修正.
                           3. 你的回复应当仅包含润色后的内容，不要添加任何额外的解释, 即使需要润色的内容为空. 请不要回复任何不在原文润色中的内容.
                        """


MAX_WORKERS = 4
MAX_RETRIES = 8


if __name__ == "__main__":
    api_key = API_KEY
    baseurl = BASEURL
    translation_model =  TRANSLATER_MODEL   
    polishing_model =  POLISHING_MODEL
    

    translator = Translator(translation_model, polishing_model, api_key, baseurl, max_retries_translater=MAX_RETRIES)
    
    # 分割需要翻译的文本
    with open(FILE_TO_TRANSLATER, 'r', encoding='utf-8') as file:
        content = file.read()  

    texts = split_string(content, min_length=8000, max_length=12000, numbered_headings=True)   

    custom_translation_prompt = TRANSLATE_PROMPT
    custom_polishing_prompt = POLISHING_PROMPT
    
    # 定义一个函数，用于翻译和润色单个文本片段
    def translate_and_polish(text, idx):
        print(f"Processing chunk {idx}...")
        return translator.translate(
            [text], 
            polish=True, 
            translation_prompt=custom_translation_prompt, 
            polishing_prompt=custom_polishing_prompt
        )[0]  

    # 使用多线程来并行处理翻译和润色
    translated_and_polished = [None] * len(texts)  
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor: 
  
        future_to_idx = {executor.submit(translate_and_polish, texts[idx], idx): idx for idx in range(len(texts))}
    
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                translated_and_polished[idx] = future.result()  # 将结果放入对应位置
            except Exception as exc:
                print(f"Chunk {idx} generated an exception: {exc}")
    
    # 打印结果
    # for idx, result in enumerate(translated_and_polished):
    #     print(f"Original: {texts[idx]}")
    #     print(f"Translated and Polished: {result}")

    with open(FILE_SAVE, 'w', encoding='utf-8') as f:
        f.writelines(f"{result}\n" for result in translated_and_polished)
