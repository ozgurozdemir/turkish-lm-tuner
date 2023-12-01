import datasets
from transformers import PreTrainedTokenizerFast
import numpy as np
from utils import (
    default_preprocess_function,
    preprocess_trnews_summarization,
    preprocess_trnews_title_generation,
    preprocess_paraphrasing,
    preprocess_nli,
    preprocess_exams_qa, 
    preprocess_exams_qg, 
    preprocess_xquad_qa, 
    preprocess_xquad_qg, 
    preprocess_mkqa_qa, 
    preprocess_mkqa_qg, 
    preprocess_wikiann_ner, 
    preprocess_xtreme_ner, 
    postprocess_text
)

dataset_mapping = {
    "offensive": "Toygar/turkish-offensive-language-detection",

    # summarization/title generation
    "tr_news": "batubayk/TR-News",

    # paraphrasing
    "opensubtitles": "mrbesher/tr-paraphrase-opensubtitles2018",
    "tatoeba": "mrbesher/tr-paraphrase-tatoeba",
    "ted": "mrbesher/tr-paraphrase-ted2013",

    # translation

    # question answering & generation
    "exams": ("exams", "crosslingual_tr"),
    "mkqa": "mkqa",
    "xquad": ("xquad", "xquad.tr"),
    "turkish-nlp-qa-dataset": "furkanakkurt1618/qa_dataset-turkish-nlp-qa-dataset-boun-llm",
    "turkish-nlp-qa-dataset-qg": "furkanakkurt1618/qg_dataset-turkish-nlp-qa-dataset-boun-llm", # wasn't on hf

    # nli
    "nli_tr": "nli_tr",

    # semantic textual similarity

    # ner
    "milliyet": "furkanakkurt1618/ner_dataset-milliyet-boun-llm", # wasn't on hf
    "wikiann": ("wikiann", "tr"),
    "xtreme": ("xtreme", "PAN-X.tr"),

    # pos tagging
    "boun": "furkanakkurt1618/pos_dataset-UD_Turkish-BOUN-v2.13-boun-llm", # wasn't on hf
    "imst": "furkanakkurt1618/pos_dataset-UD_Turkish-IMST-v2.13-boun-llm", # wasn't on hf

    # text classification
}



class DatasetProcessor:
    def __init__(self, dataset_name, task, task_format, task_mode, tokenizer_name, max_input_length, max_target_length):
        self.dataset_name = dataset_name
        self.task = task
        self.task_format = task_format
        self.task_mode = task_mode
        self.tokenizer = PreTrainedTokenizerFast.from_pretrained(tokenizer_name)
        self.max_input_length = max_input_length
        self.max_target_length = max_target_length

    def load_and_preprocess_data(self, split='train'):
        mapped_dataset = dataset_mapping[self.dataset_name]
        if type(mapped_dataset) == tuple:
            dataset = datasets.load_dataset(mapped_dataset[0], mapped_dataset[1], split=split)
        else:
            dataset = datasets.load_dataset(mapped_dataset, split=split) #.select(range(100))
        preprocess_function = self.get_preprocess_function()
        column_names = dataset.column_names
        processed_dataset = dataset.map(preprocess_function, remove_columns=column_names, batched=True)
        if self.max_input_length == -1 or self.max_target_length == -1:
            self.compute_token_length(processed_dataset)
            return
        tokenized_dataset = processed_dataset.map(self.tokenize_function, batched=True)
        return tokenized_dataset

    def compute_token_length(self, dataset):

        def get_max_length(examples):
            return {
                'input_len': [len(ex) for ex in self.tokenizer(examples['input_text'])['input_ids']],
                'target_len': [len(ex) for ex in self.tokenizer(examples['target_text'])['input_ids']]
            }

        dataset = dataset.map(get_max_length, batched=True, batch_size=8)
        max_input_length = max([i['input_len'] for i in dataset])
        max_target_length = max([i['target_len'] for i in dataset])
        mean_input_length = sum([i['input_len'] for i in dataset])/len(dataset)
        mean_target_length = sum([i['target_len'] for i in dataset])/len(dataset)
        print(f"Mean input length: {mean_input_length} Mean target length: {mean_target_length}")
        print(f"Max input length: {max_input_length} Max target length: {max_target_length}")    
        input_percent90 = np.percentile([i['input_len'] for i in dataset], 90)
        target_percent90 = np.percentile([i['target_len'] for i in dataset], 90)
        print(f"90th percentile input length: {input_percent90} 90th percentile target length: {target_percent90}")
        input_percent95 = np.percentile([i['input_len'] for i in dataset], 95)
        target_percent95 = np.percentile([i['target_len'] for i in dataset], 95)
        print(f"95th percentile input length: {input_percent95} 95th percentile target length: {target_percent95}")
        input_percent99 = np.percentile([i['input_len'] for i in dataset], 99)
        target_percent99 = np.percentile([i['target_len'] for i in dataset], 99)
        print(f"99th percentile input length: {input_percent99} 99th percentile target length: {target_percent99}")
        input_percent999 = np.percentile([i['input_len'] for i in dataset], 99.9)
        target_percent999 = np.percentile([i['target_len'] for i in dataset], 99.9)
        print(f"99.9th percentile input length: {input_percent999} 99.9th percentile target length: {target_percent999}")
    
    def get_preprocess_function(self):
        # Mapping of dataset_name and task to corresponding preprocess functions
        preprocess_functions = {
            ('tr_news', 'summarization'): preprocess_trnews_summarization,
            ('tr_news', 'title_generation'): preprocess_trnews_title_generation,
            ('opensubtitles', 'paraphrasing'): preprocess_paraphrasing,
            ('ted', 'paraphrasing'): preprocess_paraphrasing,
            ('tatoeba', 'paraphrasing'): preprocess_paraphrasing,
            ('exams', 'question_answering'): preprocess_exams_qa,
            ('exams', 'question_generation'): preprocess_exams_qg,
            ("xquad", "question_answering"): preprocess_xquad_qa,
            ("xquad", "question_generation"): preprocess_xquad_qg,
            ("mkqa", "question_answering"): preprocess_mkqa_qa,
            ("mkqa", "question_generation"): preprocess_mkqa_qg,
            ("wikiann", "ner"): preprocess_wikiann_ner,
            ("xtreme", "ner"): preprocess_xtreme_ner,
            # ... add mappings for other dataset and task type combinations
        }
        return preprocess_functions.get((self.dataset_name, self.task), default_preprocess_function)
    
    def prepend_prefix(self, examples):
        return [f'{self.task_mode}: {ex}' for ex in examples]
    
    def append_eos(self, examples):
        def append_eos_text(text):
            if text.endswith(self.tokenizer.eos_token):
                return text
            else:
                return f'{text} {self.tokenizer.eos_token}'

        return [append_eos_text(ex) for ex in examples]

    def tokenize_function(self, examples):
        if self.task_format == 'conditional_generation':
            inputs_tokenized = self.tokenizer(
                        self.prepend_prefix(examples["input_text"]),
                        padding="max_length",
                        truncation=True,
                        max_length=self.max_input_length,
                        return_token_type_ids=False,
                   )
            targets_tokenized = self.tokenizer(
                        self.append_eos(examples["target_text"]),
                        padding="max_length",
                        truncation=True,
                        max_length=self.max_target_length,
                        return_token_type_ids=False,
                   )
            return {'labels': targets_tokenized['input_ids'], **inputs_tokenized}

        return self.tokenizer(
            self.prepend_prefix(examples["input_text"]),
            padding="max_length",
            truncation=True,
            max_length=self.max_input_length,
            return_token_type_ids=False,
        )