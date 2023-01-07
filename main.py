import streamlit as st
import numpy as np
import datetime
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
import streamlit_nested_layout
from streamlit_tags import st_tags
from streamlit_tags import *
#st.set_page_config(layout="wide")
import re
import config
from typing import List,Tuple, Dict
from pymongo import MongoClient
from tqdm import tqdm

# st.image('./assets/logo.jpeg')



def hide_menu_footer(menue= True, footer= True):

    hide_streamlit_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

#hide_menu_footer()
st.markdown("# MIRA-Q 📑")
st.markdown("Mining and Investigation of Reference Attributions of Quotations")





def get_database():
 
   # Provide the mongodb atlas url to connect python to mongodb using pymongo
   CONNECTION_STRING = "mongodb+srv://ahmed:opendbnosql@cluster0.twahllt.mongodb.net/test"
 
   # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
   client = MongoClient(CONNECTION_STRING)
 
   # Create the database for our example
   return client['journals']
  
# This is added so that many files can reuse the function get_database()

def init_session_state():

    if 'lst_trends' not in st.session_state:
        st.session_state.lst_trends = []

    if 'journals_list' not in st.session_state:
        st.session_state.journals_list = []

    if 'speakers_list' not in st.session_state:
        st.session_state.speakers_lists = []

    if 'subjects_list' not in st.session_state:
        st.session_state.subjects_list = []

    if 'topics_lists' not in st.session_state:
        st.session_state.topics_lists = []

    if 'ents_list' not in st.session_state:
        st.session_state.ents_list = []

    if 'db_res' not in st.session_state:
        st.session_state.db_res = []

    if 'journal_choice' not in st.session_state:
        st.session_state.journal_choice = []

    if 'subject_choice' not in st.session_state:
        st.session_state.subject_choice = []

    if 'topics_choice' not in st.session_state:
        st.session_state.topics_choice = []

    if 'entities_choice' not in st.session_state:
        st.session_state.entities_choice = []

    if 'speaker_choice' not in st.session_state:
        st.session_state.speaker_choice = []

@st.cache
def get_model():
    return config.model.encode

def actual_search( collection_name, 
                    source= "",
                    subject= "",
                    name_space= "sources", 
                    type_query= 'single', 
                    threshoold= 0.35):

    embedder  = get_model()
    

    if type_query == 'both':
        embed = embedder([subject]).tolist()

        filter_ = {'source': {'$eq' :source}}
        matches_src = config.index.query(vector=embed, top_k=10, include_values=True, include_metadata=True, namespace=name_space, filter=filter_)

    elif type_query == 'quote':
        embed = embedder([subject]).tolist()
        matches_src = config.index.query(vector=embed, top_k=10, include_values=True, include_metadata=True, namespace=name_space)
    else:
        embed = embedder([source]).tolist()
        matches_src = config.index.query(vector=embed, top_k=10, include_values=True, include_metadata=True, namespace=name_space)


    matches_src = matches_src["matches"]

    matches_src = list(filter(lambda item: item['score'] > threshoold, matches_src))
    #print(threshoold)
    print("")
    print("")
    print('******')
    print(matches_src)
    print('')
    res = []
    for match in tqdm(matches_src):
        id_matched = match['id']

        #id_matched: vec_docid_type_parid_quoteid
        doc_id = int(id_matched.split('_')[1])
        doc_obj = list(collection_name.find({'ID': doc_id}))

        ##change this
        st.session_state.db_res.append(doc_id)
        
        par_id, q_id = int(id_matched.split('_')[3]), int(id_matched.split('_')[4])
        

        ## get the required List[tuple] for trends
        for doc in tqdm(list(doc_obj)):
            if doc['linked_entites'][par_id]:

                source = doc['linked_entites'][par_id][q_id]['Speaker']
                cue = doc['linked_entites'][par_id][q_id]['Cue']
                content = doc['linked_entites'][par_id][q_id]['Quote']

                returned_date = doc['date_publish']
                #returned_date[-1] = returned_date[-1][0:2]

                journal = doc['url']

                res.append((source, cue, content, returned_date, journal))

    st.session_state.db_res = list(set(st.session_state.db_res))
    return res


def search(
            src: str = "",
            quote: str = "",
            date: str = "",
            threshold=0.35):

    """
        Parameters:
        ----------
        src:
            DataType: str.
            Represnt: Person, organization
        subject:
            DataType: str.
            Represnt: Subject or quote to mine against.

        Returns:
        -------
            DataType: List[Tuple]
            a list of tuples. Each Tuple represnts a matched result.
            Tuple form: (source, cue, quote, Date, Journal_url)

        Steps:
        -----
        # convert all strs to embeddings (except for the Date).
        # Query VectorDB, and get a List[Dict].
            # Specify name_space.
        # Query Mongo with the results of the VectorDB.
        return a List[Tuples]
    """

    dbname = get_database()
    collection_name = dbname["gp"]


    if src and not quote:
        print('only source')
        print('')
        res = actual_search(collection_name, source= src, name_space="sources", threshoold=threshold)

    elif quote and not src:
        print('only subject')
        print('')
        res = actual_search(collection_name= collection_name, subject= quote, name_space= "quotes", type_query="quote", threshoold=threshold)

    else:
        print('both')
        print('')
        res = actual_search(collection_name= collection_name, source= src, subject= quote, name_space= "quotes", type_query='both', threshoold=threshold)

    st.session_state.lst_trends = list(set(res))
    
def extract_journal(journal_url):
    m = re.search('https?://([A-Za-z_0-9.-]+).*', journal_url)
    return m.group(1)


def trending(lst_trends):
    st.markdown("## Quotes")
    for i in range(len(lst_trends)):
        
        with st.expander('', True):

            col1, col2 = st.columns([1, 3])

            with col1:
                st.markdown(':blue[{0}]'.format(lst_trends[i][0]))
                add_vertical_space(2)
                st.write(lst_trends[i][3])

            with col2:
                st.markdown(":red[{0}]".format(lst_trends[i][1]))
                st.caption(lst_trends[i][2])
                st.write(lst_trends[i][4])



def side_bar():
    st.sidebar.markdown("## MIRA-Q")
    st.sidebar.markdown("Made with ❤️ by our team")


def filteration():
    # check for the five filters.
    # filter the database on the 5 values.
    print("DB res")
    print(st.session_state.db_res)
    print(st.session_state.journal_choice)


def filteration_area():

    col11, col22 = st.columns([4, 2])
    
    with col11:
        search_area = st.text_input("Enter some text")

    with col22:
        st.session_state['threshold'] = st.slider("similarity measure", 0.0, 1.0, 0.35)

    col333, col111, col222,  = st.columns([1, 2, 2])
    with col333:
        pass
    
    with col222:
        st.session_state['query_type'] = st.radio( "", ('Quote', 'Person/organization'), horizontal= True)
    
    if st.session_state['query_type'] == "Person/organization": query_param = 'src'
    elif st.session_state['query_type'] == "Quote": query_param = 'quote'

    with col111:
        st.button('Search', type= 'primary', key='search_but', on_click= search, kwargs= {query_param :search_area, 'threshold': st.session_state['threshold']})

    
    

    st.session_state.journals_list = list(set([extract_journal(item[-1]) for item in st.session_state.lst_trends if item]))

    st.session_state.speakers_lists = list(set([item[0] for item in st.session_state.lst_trends if item]))

    col1, col2 = st.columns([2, 2])
    with col1:
        st.session_state.journal_choice = st.multiselect("Journal" ,st.session_state.journals_list, key= "journals_tags")

        st.session_state.topics_choice = st.multiselect("Topics" ,st.session_state.topics_lists, key="topics_tags")


        st.session_state.speaker_choice = st.multiselect("Speaker" ,st.session_state.speakers_lists,key= "speakers_tags")

    
    filteration()
    with col2:
        st.session_state.subject_choice = st.multiselect("Subject" ,st.session_state.subjects_list, key="subjects_tags")

        st.session_state.entities_choice = st.multiselect('Person/org', st.session_state.ents_list, key="entities_tags")

    

        colsum, sol_insights = st.columns([0.5, 0.5])
        with colsum:
            add_vertical_space(3)
            st.button("summarize", key= "summarize_btn", type= "primary")
        with sol_insights:
            add_vertical_space(3)
            st.button("insights", key= "insight_btn", type= "primary")

    


def main():
    init_session_state()
    filteration_area()
    trending(st.session_state.lst_trends)

if __name__ == "__main__":
    main()