import numpy as np
import os
import pdftotext
from PyPDF2 import PdfFileReader
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import re
import spacy
import pandas as pd

class MyDict(dict):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
    def __getitem__(self,key):
        return dict.__getitem__(self, key.lower())
    def __setitem__(self,key,value):
        return dict.__setitem__(self,key.lower(), value)



def get_data(folder_name):
    """
    This function assumes that the folder "folder_name" is stored inside the the notebooks folder.
    Params:
    folder_name: string
    Returns: the paths to the data files in the given folder as a list.
    """
    arr = os.listdir(folder_name)
    return [os.path.join(os.getcwd(),folder_name, a) for a in arr]


def pdftotext_wrapper(input_file, options=None, output_file=None):
    """
    This function wraps the pdftotext command line tool.
    Params:
    input_file: string of path to the input pdf file.
    output_file: string of path to the output text file.
    options: string
    Returns: the text as a string.
    """
    if options is None:
        options = ""

    if output_file is None:
        output_file = ""

    check = os.popen("pdftotext " + options + " " + input_file + " " + output_file).read()
    if check == "":
        return "Success"


def extract_text(path, method):
    """
    This function extracts the text from a pdf file.
    Params:
    path: string
    method: string
    Returns: the text as a string.
    """
    if method == "pdftotext_cli":
        file_name = path.replace(os.path.dirname(data[0])+"/", "").replace(".pdf", "")
        output_dir = os.path.join(os.getcwd(), "texts")
        output_file = os.path.join(output_dir, file_name + ".txt")
        pdftotext_wrapper(data[0], "-raw", output_file) 
        with open(output_file, 'r') as f:
            #return f.read()
            return f.read().replace("\n", " ")
            #return f.readlines()

    if method == "pdftotext_python":
        with open(path, "rb") as f:
            return pdftotext.PDF(f)

    if method == "pypdf2":
        text = []
        with open(path, "rb") as f:
            pdf = PdfFileReader(f)
            text = [pdf.getPage(i).extractText() for i in range(pdf.numPages)]
            return text

def extract_entities(quote):
    words = word_tokenize(quote)
    tags = nltk.pos_tag(words)
    tree = nltk.ne_chunk(tags, binary=False)
    return set(
        " ".join(i[0] for i in t)
        for t in tree if hasattr(t, "label") and t.label() != "NE"
    )

def extract_info(folder, source="Tex"):
    """
    This function extracts the information from a paper using different methods and returns it as a dictionary with the following keys:
    {
        "Author/Authors": string,
        "Title": string,
        "Year": string,
        "Journal": string,
        "Volume": string,
        "Pages": string,
        "Abstract": string,
        "Sections": list of strings,
        "References_Sections": list of pairs of strings (refrence, section),
        "refrences": list of strings,
        "Keywords": string,
        "Language": string,
        "Source": string,
        }
    Params:
    paper: string
    source: string
    Returns: a dictionary with the extracted information.

    Reg Tips:
    1. r"\\author.*?\\\\" -> mathc from \authors command till the first \\ using lazy match in the Tex file.


    """
    info = MyDict()

    if source != "Tex":
        return info
    

    contents = get_data(folder)
 
    tex_files = [ct for ct in contents if os.path.splitext(ct)[1] == '.tex']
    bib_files = [ct for ct in contents if os.path.splitext(ct)[1] == '.bib']


    text = ""
    for tex_file in tex_files:
        with open(tex_file, "r") as f:
            temp = f.read()
            text+= "\n"+temp
    
    refs = ""
    ref_style=""
    if len(bib_files) != 0:
        ref_style="file"
        for bib_file in bib_files:
            with open(bib_file, "r") as f:
                temp = f.read()
                refs+= "\n"+temp
        # Adding an "@" sign at the end of the refs text, it will help in the extracting data using regex:
        refs+="\n @"
    else:
        ref_style="bibitem"
        refs = re.findall(r"\\bibitem.*?\\end", text, re.DOTALL)[0]
        text = text.replace(refs,"")
        refs+="\n \\bibitem"

    # Remove all comments:
    #text = re.sub(r"\%.*?\n", "", text,  re.DOTALL)

    #tmp = re.findall(r"\@\w+.[\s]*?.?(?="+"2017AREPS..45..359J"+r")(.*?)\@", refs, re.DOTALL)
    #print(tmp)
    
    # Extracting the author(s)
    #authors = re.findall(r"\\author\{(.*?)\}", text)
 
    Author_main = re.findall(r"\\author\[(.*?)\]", text)
    temp_authors = re.findall(r"\\author.*?\\\\", text, re.DOTALL)
    temp_authors = re.findall(r"\].*?\\\\", temp_authors[0], re.DOTALL)
    temp_authors = re.findall(r"(([A-Zéúßäüö]\.?\s?)*([A-Zéúßäüö][a-zéúßäüö]+\.?\s?)+([A-Zéúßäüö]\.?\s?[a-zéúßäüö]*)*)", temp_authors[0], re.DOTALL)
    Authors = [aut[0] for aut in temp_authors]


    info["Author_main"] = "; ".join(Author_main)
    info["Authors"] = "; ".join(Authors)

    # Extracting the title
    title_temp = re.findall(r"\\title.*?]", text, re.DOTALL)
    title = re.findall(r"\[(.*?)]", title_temp[0], re.DOTALL)
    info["Title"] = title[0]

    # Extracting the Abstract
    abstract_temp = re.findall(r"\\begin{abstract}(.*?)\\end{abstract}", text, re.DOTALL)
    
    # remove comments
    abstract = re.sub(r"\%.*?\n", "", abstract_temp[0],  re.DOTALL)
    info["Abstract"] = abstract


    # Find titles of sections
    section_titles = re.findall(r"\\section{(.*?)}", text, re.DOTALL)

    

    # Extract text of each section:

    sections_text = []
    Sections = MyDict()
    for s_t in section_titles:
        section_grammer= r"\\section{" + s_t + "}" + r"(.*?)" + r"\\section"
        temp =  re.findall(section_grammer, text, re.DOTALL)
        sections_text.append(temp)
        Sections[s_t] = MyDict({"text": temp[0]})
        # Same data saved as flatten version to use in neo4j, later we need to disscuss
        info[s_t + " --text"]=temp[0]
        
    info["Sections"] = Sections

    # Extracting the citeations in each section:
   
    if ref_style=="file":
        info, citations_info = extract_file_ref_style(info, refs)
    if ref_style=="bibitem":
        info, citations_info = extract_bibitem_ref_style(info, refs)
    
    return info, citations_info

def extract_bibitem_ref_style(info, refs):
    cts = []
    for s_t in info["Sections"]:
        cts_mtch = []
        
        # Citation style: \cite[][]{ref1, ref2, ref3}     
        temp_citep = re.findall(r"\\citep.*?(\[.*?\])?{(.*?)}", info["Sections"][s_t]["text"], re.DOTALL)
        if len(temp_citep)!=0:
            cts_mtch.extend(temp_citep) 
        
        # Citation style: \citet[][]{ref1, ref2, ref3} 
        temp_citet = re.findall(r"\\citet.*?(\[.*?\])?{(.*?)}", info["Sections"][s_t]["text"], re.DOTALL)
        if len(temp_citet)!=0:
            cts_mtch.extend(temp_citet)
        
        # Citation style: \citealp[][]{ref1, ref2, ref3} 
        temp_citealp = re.findall(r"\\citealp.*?(\[.*?\])?{(.*?)}", info["Sections"][s_t]["text"], re.DOTALL)
        if len(temp_citealp)!=0:
            cts_mtch.extend(temp_citealp)

        cts_in_text = []
        for c in cts_mtch:
            if len(c)>=1:
                if type(c[-1])==tuple:
                    cts_in_text.append(list(c[-1]))
                else:
                    cts_in_text.append(c[-1])
        
         
        info["Sections"][s_t]["citations"] = [t.split(",") for t in cts_in_text]
    
        # Same data saved as flatten version to use in neo4j, later we need to disscuss
        if len(cts_in_text)!=0:
            cts = [t.split(",") for t in cts_in_text]

        cts_flatten_temp= [c for ct in cts for c in ct]
        cts_flatten = []
        for c in cts_flatten_temp:
            if type(c) is list:
                cts_flatten.append(c[0].strip())
            else:
                cts_flatten.append(c.strip())

        cts_info = []
        for bib_item in cts_flatten:
            bib_item_section = re.findall(r"\{[\s]*?"+bib_item+r"[\s]*?\}.*?\\bibitem", refs, re.DOTALL)
            title = re.findall(r"(?i)title.*?{(.*?)}", bib_item_section[0],re.DOTALL)
            doi = re.findall(r"(?i)doi.*?{(.*?)}", bib_item_section[0],re.DOTALL)
            
            cts_info.append([bib_item,title, doi])

        info[s_t + " --cts"] = cts_info
    
    
    return info, refs


def extract_file_ref_style(info, refs):
    cts = []
    for s_t in info["Sections"]:
        cts_mtch = []
        
        # Citation style: \cite[][]{ref1, ref2, ref3}     
        temp_citep = re.findall(r"\\citep.*?(\[.*?\])?{(.*?)}", info["Sections"][s_t]["text"], re.DOTALL)
        if len(temp_citep)!=0:
            cts_mtch.extend(temp_citep) 
        
        # Citation style: \citet[][]{ref1, ref2, ref3} 
        temp_citet = re.findall(r"\\citet.*?(\[.*?\])?{(.*?)}", info["Sections"][s_t]["text"], re.DOTALL)
        if len(temp_citet)!=0:
            cts_mtch.extend(temp_citet)
        
        # Citation style: \citealp[][]{ref1, ref2, ref3} 
        temp_citealp = re.findall(r"\\citealp.*?(\[.*?\])?{(.*?)}", info["Sections"][s_t]["text"], re.DOTALL)
        if len(temp_citealp)!=0:
            cts_mtch.extend(temp_citealp)

        cts_in_text = []
        for c in cts_mtch:
            if len(c)>=1:
                if type(c[-1])==tuple:
                    cts_in_text.append(list(c[-1]))
                else:
                    cts_in_text.append(c[-1])
        
        info["Sections"][s_t]["citations"] = [t.split(",") for t in cts_in_text]
    
                # Same data saved as flatten version to use in neo4j, later we need to disscuss
        if len(cts_in_text)!=0:
            cts = [t.split(",") for t in cts_in_text]

        cts_flatten_temp= [c for ct in cts for c in ct]
        cts_flatten = []
        for c in cts_flatten_temp:
            if type(c) is list:
                cts_flatten.append(c[0].strip())
            else:
                cts_flatten.append(c.strip())

        cts_info = []
        for bib_item in cts_flatten:
            bib_item_section = re.findall(r"\@\w+.[\s]*?.?(?=[\s]*?"+c+r")(.*?)\@", refs, re.DOTALL)
            title = re.findall(r"(?i)title.*?{(.*?)}", bib_item_section[0],re.DOTALL)
            doi = re.findall(r"(?i)doi.*?{(.*?)}", bib_item_section[0],re.DOTALL)
            cts_info.append([bib_item,title, doi])

        info[s_t + " --cts"] = cts_info

    citations_info = MyDict()
    # Adding citations from bib files to the sections:
    bib_cts = []
    all_bib_cts = []
    for s_t in info["Sections"]:
        all_cts = info["Sections"][s_t]["citations"]
        for cts in all_cts:
            for ct in cts:
                if len(ct)==1:
                    tmp = re.findall(r"(\@\w+.[\s]*?.?(?=[\s]*?"+ct[0]+r")(.*?))\@", refs, re.DOTALL)
                else:
                    tmp = re.findall(r"(\@\w+.[\s]*?.?(?=[\s]*?"+ct+r")(.*?))\@", refs, re.DOTALL)
              #  print(tmp)
                bib_cts.append(tmp)
            all_bib_cts.append(bib_cts)
        citations_info[s_t] = all_bib_cts
    
    return info, citations_info