from transformers import MarianMTModel, MarianTokenizer
from dotenv import load_dotenv
import os
load_dotenv()

model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-ar")
tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-ar")

save_directory = os.getenv('MODEL_DIRECTORY', './model')

if not os.path.exists(save_directory):
    os.makedirs(save_directory)

model.save_pretrained(save_directory)
tokenizer.save_pretrained(save_directory)