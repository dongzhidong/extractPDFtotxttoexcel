# -*- coding: UTF-8 -*-

"""
1.加载一个指定路径文件夹内的所有pdf文内容
2.解析所有pdf内容并提取指定内容
3.把解析出来的指定内容写入Excel表格
"""

#################
import xlwt  # 写入文件
import xlrd  # 打开excel文件
from xlutils.copy import copy

import os
import re
import sys
import importlib
import threading

importlib.reload(sys)
from pdfminer.pdfparser import PDFParser,PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBoxHorizontal,LAParams
from pdfminer.pdfinterp import PDFTextExtractionNotAllowed
import logging
logging.basicConfig(level=logging.ERROR)

__author__ = "dong"
__version__ = "20200325v1"


# 读取一个文件夹目录下所有PDF文档路径,返回所有PDF文件的绝对路径
def loadPDF(file_path, stock_num_list=None):
    pdf_files = {}  # 保存文件地址和名称：name：path
    files = os.listdir(file_path)
    for file in files:
        if os.path.splitext(file)[1] == '.pdf':  # 判断是否为PDF文件
            if stock_num_list is None or (stock_num_list is not None and file[0:6] in stock_num_list):
                abso_Path = os.path.join(file_path, file)
                stock_num = file[0:6]
                pdf_files[file] = (stock_num, abso_Path)
    return pdf_files


# 解析PDF文件，转为txt格式
def parsePDF(PDF_path, TXT_path):
    if not os.path.isdir(os.path.dirname(TXT_path)):
        os.makedirs(os.path.dirname(TXT_path))

    with open(PDF_path, 'rb')as fp:  # 以二进制读模式打开
        praser = PDFParser(fp)  # 用文件对象来创建一个pdf文档分析器
        doc = PDFDocument()  # 创建一个PDF文档
        praser.set_document(doc)  # 连接分析器与文档对象
        doc.set_parser(praser)

        # 提供初始化密码
        # 如果没有密码 就创建一个空的字符串
        doc.initialize()

        # 检测文档是否提供txt转换，不提供就忽略
        if not doc.is_extractable:
            raise PDFTextExtractionNotAllowed
        else:
            rsrcmgr = PDFResourceManager()  # 创建PDf 资源管理器 来管理共享资源
            laparams = LAParams()  # 创建一个PDF设备对象
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)  # 创建一个PDF解释器对象
            page_index=0
            # 循环遍历列表，每次处理一个page的内容
            for page in doc.get_pages():  # doc.get_pages() 获取page列表
                print('\r正在处理.. '+os.path.basename(PDF_path)+' page:{}'.format(page_index),end='')
                page_index+=1
                interpreter.process_page(page)
                layout = device.get_result()  # 接受该页面的LTPage对象
                # 这里layout是一个LTPage对象 里面存放着 这个page解析出的各种对象 一般包括LTTextBox, LTFigure, LTImage, LTTextBoxHorizontal 等等 想要获取文本就获得对象的text属性，
                for x in layout:
                    if isinstance(x, LTTextBoxHorizontal):
                        with open(TXT_path, 'a', encoding='UTF-8', errors='ignore') as f:
                            results = x.get_text()
                            # print(results)
                            f.write(results + '\n')
    print('\r'+os.path.basename(PDF_path)+' 处理完成')
    print(' ',end='')




# 加载目标股票代码
def getStackNum(excel_path):
    book = xlrd.open_workbook(excel_path)  # 打开一个wordbook
    sheet_ori = book.sheet_by_name('Sheet1')
    return sheet_ori.col_values(0, 0, sheet_ori.nrows)


# 从Excel中加载关键词
def loadKeyWords(excel_path):
    book = xlrd.open_workbook(excel_path)  # 打开一个wordbook
    sheet_ori = book.sheet_by_name('Sheet1')
    return sheet_ori.row_values(0, 1, sheet_ori.ncols)


# 加载txt列表寻找关键词并保存到excel
def matchKeyWords(txt_paths, excel_path, keyWords, outfile_name):
    words_ = []  # 保存所有句子
    for index,file in enumerate(txt_paths):
        print("running: %s: %d/%d "%(file,index+1,len(txt_paths)))
        word_all = {}  # 单词出现频率次：word：num
        line123=''
        if os.path.splitext(file)[1] == ".txt":
            with open(file, "r", encoding='utf-8', errors='ignore')as fp:
                text = fp.readlines()
                for word in keyWords:
                    line_all=[]
                    num = 0
                    for line in text:
                        if num<5:
                            line123=line123+line
                            num+=1
                            continue
                        num=0
                        line=line123.strip()
                        line=re.sub(' ','',line)
                        line123=''
                        if line.count(word):
                            line_all.append(line)
                    #     查找
                    word_all[word] = line_all
                pdf_name = os.path.basename(file).split(".")[0]+".pdf"
                words_.append((word_all, pdf_name))

    # 保存到Excel
    book = xlrd.open_workbook(excel_path)  # 打开一个wordbook
    copy_book = copy(book)
    sheet_copy = copy_book.get_sheet("Sheet1")
    row_x=1
    max_row_tem=0
    for index, one in enumerate(words_):
        word_f = one[0]
        pdf_name = one[1]
        row_x=row_x+max_row_tem
        max_row_tem=0
        tem=0
        for i in range(len(keyWords)):
            tem=max(tem,len(word_f[keyWords[i]]))
        for i in range(tem):
            for j in range(len(keyWords)):
                sheet_copy.write(row_x+i,  j+ 1, ' ')
        for ind, word in enumerate(keyWords):
            row_x_temp = row_x
            word_write=word_f[word]
            if word_write!=[]:
                max_row_tem = max(max_row_tem, len(word_write))
                for i in range(len(word_write)):
                    sheet_copy.write(row_x_temp, ind + 1, str(word_f[word][i])[1:-1])
                    row_x_temp+=1
        sheet_copy.write(row_x, 0, pdf_name)
    copy_book.save( outfile_name + ".xls")

# os.path.basename(excel_path)
if __name__ == '__main__':
    excel_path = "target.xlsx"
    # if len(sys.argv) < 2:
    #     print("less parameters to run...")
    # else:
    #     path = str(sys.argv[1])
    #     outfile_name = sys.argv[2]
    print('---PDF信息提取程序---')
    print('说明：程序从当前文件夹target.xlsx第二列读入关键词，先将pdf文件夹各pdf文件转为temp_txt文件夹文本格式，搜索并将关键词所在句存入当前文件夹中新建的输出文件中。')
    print('--------------------')
    path=input('输入pdf所在文件夹路径：')
    outfile_name=input("输入输出excel文件名：")


    # 程序开始
    print("Now the program is running...")
    txtpath = os.path.join(os.path.dirname(path),'temp_txt')
    for root, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            if os.path.splitext(full_path)[1] == '.pdf':
                parsePDF(full_path,os.path.join(txtpath,file.split('.')[0]+'.txt'))

    txt_path = []
    for root, dirs, files in os.walk(txtpath):
        for file in files:
            full_path = os.path.join(root, file)
            txt_path.append(full_path)
    print("match keywords...")
    matchKeyWords(txt_path, excel_path, loadKeyWords(excel_path),outfile_name )
    print("done!")
    input('回车键结束~~')
    print("done!")
