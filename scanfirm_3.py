#!/usr/bin/python
# -*- coding: UTF-8 -*- 
import os,sys,datetime,logging
import json
import shutil,subprocess
import operator as op

suffix_list = [".web", ".bin", ".BIN", ".dav", ".img", ".dmg"]
num_of_matched_firm = 0
num_of_total_firm = 0
RESULT_LOG = '../log/result.dat'
RUN_LOG = '../log/runlog.log'


def InitLogger():
    logger = logging.getLogger('firmlogger')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(RUN_LOG)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(funcName)s [%(levelname)s]:  %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    ch.setLevel(logging.WARNING)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
    
logger = InitLogger()


def ExtractFiles(path):
    logger.debug('Start Extract Compressed Firmwares....')
    for root, dirs, files in os.walk(path):
        for f in files:
            filepath = os.path.join(root,f)
            try:
                if op.eq(f[-4:],'.zip')==True:
                    precmd = 'unzip -l "' + filepath +'"'
                    process = subprocess.Popen(precmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    process.wait()
                    unzip_out = process.stdout.read().decode('utf-8')
                    unzip_flag = 0
                    for i in range(len(suffix_list)):
                        suffix = suffix_list[i]
                        if suffix in unzip_out:
                            unzip_flag = 1
                    if unzip_flag == 1:
                        logger.info('unzip file: {}'.format(filepath))
                        cmd = 'unzip -q -o "' + filepath + '" -d "' + filepath[:-4] + '"'
                        os.system(cmd)
                        os.remove(filepath)
                elif op.eq(f[-4:],'.rar')==True:
                    logger.info('unrar file: {}'.format(filepath))
                    if not os.path.exists(filepath[:-4]):
                        os.mkdir(filepath[:-4])
                    cmd = 'unrar x -inul -y -o+ "' + filepath + '" "' + filepath[:-4] + '"'
                    #print cmd
                    os.system(cmd)
                    os.remove(filepath)
            except Exception as e:
                logger.error('[-] Error in ExtractFiles, file: {}, info: {}'.format(filepath, e))
                continue


def BinwalkFiles(path, keywords):
    global num_of_matched_firm
    global num_of_total_firm
    logger.debug('Start Binwalk Firmwares....')
    for root, dirs, files in os.walk(path):
        for file in files:
            if(file[-4:] in suffix_list):
                num_of_total_firm = num_of_total_firm + 1
                firm_path = os.path.join(root,file)
                extrdir_path = os.path.join(root, '_{}.extracted'.format(file))
                logger.info('HANDLE FILE: {}'.format(firm_path))
                fsize = os.path.getsize(firm_path) / float(1024*1024)
                if fsize < 100:
                    try:
                        cmd = 'binwalk -eq "' + firm_path + '" -C "' + root + '"'
                        logger.info('command = {}'.format(cmd))
                        os.system(cmd)
                        if os.path.exists(extrdir_path):
                            #在解包目录中查找关键词，之后删除目录
                            logger.debug('binwalk SUCCESS, start find str.')
                            matchSuccess = FindStr(firm_path, extrdir_path, keywords)
                            if matchSuccess:
                                num_of_matched_firm = num_of_matched_firm + 1
                                logger.warning('[+] find str in {}'.format(firm_path))
                            shutil.rmtree(extrdir_path)
                            logger.debug('remove dir: {}'.format(extrdir_path))
                        else:
                            logger.info('binwalk FAILED, maybe the firmware is encrypted.')
                    except Exception as e:
                        logger.error('[-] Error in BinwalkFiles, file: {}, info: {}'.format(firm_path, repr(e)))
                        if os.path.exists(extrdir_path):
                            shutil.rmtree(extrdir_path)
                        continue

##find keywords in files of a firmware
def FindStr(firmpath, dirpath, keywords):
    logger.debug('Searching keywords in {}.....'.format(firmpath))
    logf = open(RESULT_LOG,"a+")   
    result = 0
    data = {}
    info = {}
    for root, dirs, files in os.walk(dirpath):
        #firmware中的一个文件
        for file in files:
            try:
                file_path = os.path.join(root,file)
                #print(file_path)
                cmd = 'strings -d {} | grep -E "{}"'.format(file_path, keywords)
                #print (cmd)
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                process.wait()
                wordslist = process.stdout.readlines()
                #print (wordslist)
                if(len(wordslist)>0):
                    result = 1
                    logger.info('       keyword found in {}'.format(file_path))
                    words = ''
                    for word in wordslist:
                        tmpword = word.decode('utf-8')
                        words = words + tmpword.strip() + ' | '
                    info[file_path] = words
            except Exception as e:
                logger.error('[-] Error in FindStr, file: {}, info: {}'.format(file_path, repr(e)))
    if result==1:
        logger.debug('Generate JSON data, write into result file.')
        data['files'] = info
        data['firmfile'] = firmpath
        jsonstr = json.dumps(data, sort_keys=True, indent=4, separators=(', ', ': '))
        #jsonstr = json.dumps(data)
        logf.write(jsonstr + '\n\n')
    logf.close()
    return result
    
    
def main(path, keywords):
    logger.debug('********** Boot. Path = {}, Keywords = {} ************'.format(path, keywords))
    ExtractFiles(path)                 
    BinwalkFiles(path, keywords)
    

if __name__ == "__main__":
    if(len(sys.argv) != 3):
        print(len(sys.argv))
        print("Usage: python scanfirm.py [path] [key1|key2|key3..]")
        exit()
    path = sys.argv[1]
    keywords = sys.argv[2]
    starttime = datetime.datetime.now()
    main(path, keywords)
    endtime = datetime.datetime.now()
    usetime = endtime - starttime
    print ('use time: {}, {} matched in {} firmwares.'.format(usetime, num_of_matched_firm, num_of_total_firm))