from scipy.io import wavfile
import matplotlib.pyplot as plt
from os.path import abspath
import os
import pandas as pd
import numpy as np
import dawdreamer as daw
from itertools import repeat
import math
import paramiko
import datetime
import simpleaudio as sa




SAMPLE_RATE = 44100 # SAMPLE_RATE(hz)
BUFFER_SIZE = 512 # For speed when not using automation, choose a larger buffer such as 512.
DSP_PATH = abspath("FM_op1.dsp")  # Must be absolute path


def init_dsp():
	engine = daw.RenderEngine(SAMPLE_RATE, BUFFER_SIZE)
	faust_processor = engine.make_faust_processor("faust")
	faust_processor.set_dsp(DSP_PATH)  # You can do this anytime.

	assert(faust_processor.compile())

	return engine, faust_processor, pd.DataFrame(faust_processor.get_parameters_description())





def make_automation(dir, fname, mapping, sonification_rate, dsp_info):


	datasets_dir = dir + fname + '_datasets.csv'


	#get parameters' max and min.
	max_parameter = pd.Series(data=dsp_info['max'].to_list(), index=dsp_info.name.to_list())
	min_parameter = pd.Series(data=dsp_info['min'].to_list(), index=dsp_info.name.to_list())

	#read datasets and store as DataFrame
	datasets = pd.read_csv(datasets_dir)
	#get the length of datasets
	dataset_length =  len(datasets)
	#calculate ideal duration. Sonification sound will have the same duration.
	Duration = sonification_rate * len(datasets) * pow(10,-3)

	#automation has dsp_info as columns. Now automation does not have any value.
	automation = pd.DataFrame(columns=dsp_info.name.to_list())

	#make automation from datasets selected by mapping.

	for i in range(len(mapping)):
		if mapping[i] != 'Disabled':
			max_datasets = max(datasets[mapping[i]])
			#get automation adjusted to SAMPLE_RATE
			# automation[mapping.index[i]] = np.repeat(datasets[mapping[i]]/max_datasets * max_parameter[mapping.index[i]], int(Duration*SAMPLE_RATE/len(datasets)))
			target_station = mapping[i]
			target_parameter = mapping.index[i]

			#map the range of dataset to the range of parameter
			#データセットの値域をdspのパラメーターの値域にマッピングする

			#if max_datasets is 0, dision by zero will be occured.
			if max_datasets !=0:
				tmp_list = datasets[target_station]/max_datasets * (max_parameter[target_parameter] - min_parameter[target_parameter]) + min_parameter[target_parameter]
			
			else:
				tmp_list = np.repeat(0,dataset_length)
			
			#As 44100(SAMPLE_RATE) data sampled per second, the automation data needs to be stretched.
			#一秒間に44100(SAMPLE_RATE)個のデータがオートメーションから読み込まれるので、それに合わせて配列をストレッチする。
			automation[target_parameter] = np.repeat(tmp_list, int(Duration*SAMPLE_RATE/dataset_length))

	duration = len(automation)/SAMPLE_RATE

	#Duration... Ideal duration
	#duration... Actual duration

	return automation, duration





def render(engine, file_path, duration):

	engine.render(duration)

	output = engine.get_audio()

	amplitude = np.iinfo(np.int16).max

	output = amplitude * output

	if file_path is not None:

		wavfile.write(file_path, SAMPLE_RATE, output.transpose().astype(np.int16))

	return True






def make_sound(faust_processor,engine,automation,duration,mapping,filename):

	for i in range(len(mapping)):
		target_station = mapping[i]
		target_parameter = mapping.index[i]

		if target_station != 'Disabled':
			faust_processor.set_automation(target_parameter,np.array(automation[target_parameter]))


	graph = [
		(faust_processor, [])   
	]

	assert(engine.load_graph(graph))


	print(automation)


	render(engine, file_path=filename, duration= duration)

	print('sonification is finished')
	print('output file: ' + filename)







def sonification(mapping, sonification_rate, dir, fname):

	dir = dir + '/' + fname + '/'
	output_file = dir + fname + '.wav'

	# Make an engine. We'll only need one.

	#get information of dsp_parameters
	engine, faust_processor, dsp_info = init_dsp()

	
	automation, duration = make_automation(dir, fname, mapping, sonification_rate, dsp_info)


	make_sound(faust_processor,engine,automation,duration,mapping,output_file)

	print('>sonification is finished.')





def make_query(start_day, end_day, target):

	start_day = "'" + start_day + " 00:00:00'"
	end_day = "'" + end_day + " 00:00:00'"

	query = "select time, sname, " + target + " from data where sname in (:str) and time between " + start_day + " and " + end_day + " order by time, sname"

	return query




def ssh(start_day, end_day, target, threshold, minSup, maxPer, save_dir, save_fname):

	save_dir = save_dir + '/' + save_fname
	os.makedirs(save_dir, exist_ok=True) 
	fname_datasets = save_dir + '/' + save_fname  + '_datasets.csv'
	fname_patterns = save_dir + '/' + save_fname + '_patterns.csv'


	stations = ""

	#server info
	host='skytree.u-aizu.ac.jp'
	host_username=''	
	host_password=''
	
	#make paramiko instance
	client = paramiko.SSHClient()
	client.load_system_host_keys()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(hostname=host, username=host_username, password=host_password, timeout=10, look_for_keys=False)


	print('> connected to ' + host)

	#get six stations randomly
	CMD= "cd Sonification; psql -U yoshiki -d airpollution < \"random_station.sql\" --no-password --csv > stations.csv;"
	CMD= CMD+ ' sed -i \'/sname/d\' stations.csv; cat  stations.csv'
	stdin,stdout,_ = client.exec_command(CMD)

	for index, line in enumerate(stdout):
		stations = str(stations) + "\'" + str(line).rstrip() + "\', "

	stations = stations[:-2]

	stations = '"' + stations + '"'


	stdin.close()


	print('> get six stations randomly')


	#make query including start day, end day, and target pollutant
	query = make_query(start_day, end_day, target)
	CMD = 'echo "' + query + '" > /home/yoshiki/Sonification/query.sql'
	stdin,stdout,stderr = client.exec_command(CMD)

	for line in stderr:
		print('>>' + line)
	
	for line in stdout:
		print('>' + line)

	stdin.close()


	print('> get datasets and patterns')

	#create dataset and do pami on server
	CMD= "cd Sonification ; psql -U yoshiki -d airpollution < \"query.sql\" --no-password --csv -v str=" + stations + " > query_result.csv ;"
	CMD= CMD + "python3.8 mining.py " + str(threshold) + " " + str(minSup) + " " + str(maxPer) #+ "" + str(target)

	stdin,stdout,stderr = client.exec_command(CMD)

	stdin.close()

	for line in stderr:
		print('>>' + line)

	for line in stdout:
		if line == 'err: code -1':
			return
		print('>  ' + line)

	try:
		#start SFTP session
		sftp_connection = client.open_sftp()
	
		#download patterns from the server
		sftp_connection.get('Sonification/datasets.csv', fname_datasets)
		sftp_connection.get('Sonification/patterns.csv', fname_patterns)

	finally:

		client.close()
		print('4')


def draw_plot(fig):
	plt.show(block=False)
	return 'Start'


def del_plot(fig):

    # plt.cla(): Axesをクリア
    # plt.clf(): figureをクリア
    # plt.close(): プロットを表示するためにポップアップしたウィンドウをクローズ

    plt.close()