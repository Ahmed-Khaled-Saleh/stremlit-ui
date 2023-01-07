import pinecone
import json
from typing import Iterator, Tuple, List
import numpy as np
import config
from tqdm import tqdm
import time

def setup_credentials(index_name: str = "example-trial"):
    pinecone.init(api_key="2e416414-ac9b-4231-a06c-ff1fc3d40b30", environment="us-west1-gcp")

    if index_name in pinecone.list_indexes():
        pinecone.delete_index("example-trial")

    pinecone.create_index("example-trial", dimension=384)

class Batch_generator:
    
    def __init__(self, batch_size: int = 32) -> None:
        self.batch_size = batch_size
    
    def to_batches(self, data_list: list) -> Iterator[dict]:

        splits = self.splits_num(len(data_list))
        if splits <= 1:
            yield data_list

        else:
            for chunk in np.array_split(data_list, splits):
                yield chunk
    
    def splits_num(self, elements: int) -> int:
        return round(elements / self.batch_size)
    
    __call__ = to_batches

class Embedder:
    

    def __init__(self) -> None:
        self.titles_vect, self.maintext_vect, self.paragraphs_vect,\
        self.source_vec, self.quotes_vect = [], [] , [], [], []

    def get_vec(self,
                embedding:List[np.array],
                doc_id:str,
                meta_data: dict,
                txt_type='main',
                par_id: int = -1,
                quote_idx: int= -1,
                speaker_name: str = "") -> tuple:

        vecs = []
        if len(embedding.shape) != 2 or embedding.shape[0] < 2:
            embedding = [embedding]

        for i, embed in enumerate(embedding):
            vec_values = embed.tolist()

            if txt_type == 'paragraphs':
                par_id = i
            
            if txt_type == 'quotes':
                new_meta_data = dict(meta_data)
                new_meta_data['source'] = speaker_name

                vec_name = ('vec_{0}_{1}_{2}_{3}'.format(doc_id, txt_type, par_id, quote_idx))
                vecs.append((vec_name, vec_values, new_meta_data))
                return vecs

            print(txt_type)
            print(meta_data)
            print('')
            vec_name = ('vec_{0}_{1}_{2}_{3}'.format(doc_id, txt_type, par_id, quote_idx))
            vecs.append((vec_name, vec_values, meta_data))

        return vecs

    def get_embedding(self, corpus: dict) -> list :

        for doc in corpus:
            
            doc_topics = doc['topics']

            meta_data = {
                'doc_id' : doc['ID'],
                'date': doc['date_publish'],
                'journal': doc['source_domain'],
                'url': doc['url']
            }

            title = doc['title']
            titles_embedding = config.model.encode(title)
            self.titles_vect = self.get_vec(titles_embedding, meta_data['doc_id'], meta_data, 'title')
            
            self.source_vec, self.quotes_vect, self.sum_quote = [], [], []
            for i, par in enumerate(doc['linked_entites']):
                if par:
                    for j, quote in enumerate(par):

                        em_src = config.model.encode(quote['Speaker'])
                        l1 = self.get_vec(em_src, meta_data['doc_id'], meta_data, 'sources', i, j)
                        self.source_vec.extend(l1)

                        em_q = config.model.encode(quote['Quote'])
                        l2 = self.get_vec(em_q, meta_data['doc_id'], meta_data, 'quotes', i, j, quote['Speaker'])
                        self.quotes_vect.extend(l2)

                        em_q_sum = config.model.encode(quote["Quote_summarization"])
                        l3 = self.get_vec(em_q_sum, meta_data['doc_id'], meta_data, 'quote_sum', i, j, quote['Speaker'])
                        self.sum_quote.extend(l3)

            #print(source_vec)
            main_text = doc['maintext']
            embed_main_text = config.model.encode(main_text)
            self.maintext_vect = self.get_vec(embed_main_text, meta_data['doc_id'], meta_data, 'maintext')

            paragraphs = doc['paragraphs']
            embed_paragraphs = config.model.encode(paragraphs)
            self.paragraphs_vect = self.get_vec(embed_paragraphs, meta_data['doc_id'], meta_data, 'paragraphs')

            main_sum = doc['maintext_summerization']
            embed_main_sum = config.model.encode(main_sum)
            self.main_sum_vec = self.get_vec(embed_main_sum, meta_data['doc_id'], meta_data, 'main_sum')

            par_sum = doc['paragraphs_summerization']
            embed_par_sum = config.model.encode(par_sum)
            self.par_sum_vec = self.get_vec(embed_par_sum, meta_data['doc_id'], meta_data, 'par_sum')


            


        return self.titles_vect, self.maintext_vect, self.paragraphs_vect, self.source_vec, self.quotes_vect, self.sum_quote, self.main_sum_vec, self.par_sum_vec

def create_vector_space(vectors: list, name_space:str):
    index = pinecone.Index("example-trial")
    index.upsert(
        vectors = vectors,
        namespace = name_space
    )
    return index

class Ingester:

    def __init__(self, json_file_path, batch_size= 32):
        setup_credentials()
        with open(json_file_path, encoding='utf-8', errors='ignore') as json_doc:
            self.corpus = json.load(json_doc, strict=False)

        self.title_namespace = 'titles'
        self.maintext_namespace = 'maintext'
        self.paragraphs_namespace = 'paragraphs'
        self.sources_namespaces = 'sources'
        self.quotes_name_space = 'quotes'
        self.quote_sumarization = "quote_sum"
        self.main_sum = "main_sum"
        self.par_sum = "par_sum"
        
        self.lst_name_spaces = [self.title_namespace,\
                                self.maintext_namespace,\
                                self.paragraphs_namespace,\
                                self.sources_namespaces,\
                                self.quotes_name_space,\
                                self.quote_sumarization,\
                                self.main_sum,\
                                self.par_sum]

        self.batch_gen = Batch_generator(batch_size)
        self.embedder = Embedder()
        self.vector_space_creator = create_vector_space

    def ingest(self):
        for batched_data in tqdm(self.batch_gen(self.corpus)):
            all_vecs = self.embedder.get_embedding(batched_data)

            for i, name_space in enumerate(self.lst_name_spaces):
                print('+++++++ Starting Ingestion +++++++')
                #try:
                index = self.vector_space_creator(all_vecs[i], name_space= name_space)
                print(index.describe_index_stats())
                print("Done ingesting in {0} name space".format(name_space))
                print('+++++++ Ingestion Done +++++++')

                # except:
                #     print("------- ERROR While Ingesting the data -------")
        return index

ingester_obj = Ingester('./new_data_v7.json', batch_size= 1)
index = ingester_obj.ingest()
print(index.describe_index_stats())


# pinecone.init(api_key="4bdfcfb1-fbce-4b38-be35-080b6c96dce4", environment="us-west1-gcp")
# index = pinecone.Index("example-trial")
# # vec = config.model.encode(["Mr Sudani"])
# # print(index.query(vector=vec.tolist(), top_k=3, include_values=True, include_metdata= True, namespace='sources', filter={'source': 'Mr Sudani'}))
# print(index.describe_index_stats())




# class Extractor:
#     pass


# print(index.describe_index_stats())