from transformers import MarianMTModel, MarianTokenizer
from dotenv import load_dotenv
import os

load_dotenv()

load_dir = "./model"

model = MarianMTModel.from_pretrained(load_dir)
tokenizer = MarianTokenizer.from_pretrained(load_dir)


