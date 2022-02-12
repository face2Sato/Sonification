from scipy.io import wavfile
import matplotlib.pyplot as plt
import matplotlib.cm as cm
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
from PAMI.periodicFrequentPattern.basic import PFPGrowth as alg 
import psycopg2
from sshtunnel  import SSHTunnelForwarder

DEMO =  True



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





# calimaps...xxxx10calima

def pattern_mining(outputfile, minSup, maxPer):
	
	obj = alg.PFPGrowth('tmp.csv', minSup, maxPer) 

	#use obj = alg.fpGrowth(inputFile, minSup,sep=',')  to override the default tab space separator with comma
	obj.startMine()  #start the mining process
	df = obj.getPatternsAsDataFrame()      #store the generated patterns in a file
	
	os.remove('tmp.csv')
	
	if isinstance(df, pd.DataFrame) is True:
		df = df.sort_values(by = 'Support', ascending = False)
		print('Patterns were found.')
		print(df)
		df.to_csv(outputfile)
		
		return 0
		
	else:
		print('Patterns were not found.')
		
		return -1





def make_query(start_day, end_day, target, snames_str):

	start_day = "'" + start_day + " 00:00:00'"
	end_day = "'" + end_day + " 00:00:00'"
	# snames ... 's1', 's2', 's3'

	query = 'select time, sname, ' + target + ' from data where sname in (' + snames_str + ') and time between ' + start_day + ' and ' + end_day + ' order by time, sname'

	return query


def select_stations():

	server = SSHTunnelForwarder(
				("163.143.87.108", 22),
				ssh_username="yoshiki",
				ssh_password="yosi@810",
				ssh_pkey=None,
				remote_bind_address=('localhost', 5432),
	)

	server.start()

	conn = psycopg2.connect(
		host='163.143.87.108',
		port='5432',
		database='airpollution',
		user='yoshiki',
		password='yoshiki4916',
	)
	# snames...df
	if DEMO is True:
		snames = ['28201090', '22221010', '23103020', '41203010', '46202520', '30205030']
	else:
		snames = pd.read_sql(sql='select sname from station_info order by random() limit 6', con=conn)
		# snames...list (['s1','s2',...,'s6'])
		snames = snames['sname'].to_list()
	
	conn.close()
	server.stop()

	return snames






def get_dataset(start_day, end_day, pollutant, snames):

	server = SSHTunnelForwarder(
				("163.143.87.108", 22),
				ssh_username="yoshiki",
				ssh_password="yosi@810",
				ssh_pkey=None,
				remote_bind_address=('localhost', 5432),
	)

	server.start()

	conn = psycopg2.connect(
		host='163.143.87.108',
		port='5432',
		database='airpollution',
		user='yoshiki',
		password='yoshiki4916',
	)

	# snames_str...str ("'s1','s2',...'s6'")
	snames_str = map(lambda x: "'"+ x + "'",snames)
	snames_str = ','.join(snames_str)

	print('selected stations are')
	print(snames,type(snames))


	query=make_query(start_day, end_day, pollutant,snames_str)


	dataset = pd.read_sql(sql=query, con=conn)

	conn.close()

	server.stop()

	return dataset




def create_datasets(df,snames,outputfile):

	def select(df,station,target):
		return df[df['sname'] == station ][{'time',target}].rename(columns = {target : station })

	s=snames
	
	target = df.columns[2]

	# df1 = pd.merge(df[df['sname'] == s[0]][{'time',target}].rename(columns = {target:s[0]}),df[df['sname'] == s[1]],on='time')

	df1 = pd.merge(select(df,s[0], target), select(df,s[1], target), on='time', how='outer')
	df1 = pd.merge(df1, select(df, s[2], target), on='time', how='outer')
	df2 = pd.merge(select(df,s[3], target) , select(df,s[4], target) ,on='time', how='outer')
	df2 = pd.merge(df2, select(df, s[5], target), on='time', how='outer')
	df0 = pd.merge(df1, df2, on='time', how='outer')
	
	df0 = df0.reindex(columns=['time',s[0],s[1],s[2],s[3],s[4],s[5]])
	df0 = df0.set_index('time')

	df0 =df0.rename(columns={s[0]:'s1 ',s[1]:'s2 ',s[2]:'s3 ',s[3]:'s4 ',s[4]:'s5 ',s[5]:'s6 '})
	
	high_fence = max(df0.quantile(0.99) * 1.5)

	df0 = df0[df0>0]

	df0 = df0[df0<high_fence].fillna(0)

	df0.to_csv(outputfile)






def data_convert(df, stations, threshold):

	#df.columns[2] shows the column which has air pollutant values
	target = df.columns[2]
	
	df = df.replace(
		{
			stations[0] : 's1 ',
			stations[1] : 's2 ',
			stations[2] : 's3 ',
			stations[3] : 's4 ',
			stations[4] : 's5 ',
			stations[5] : 's6 '
		}
	)


	t = df['time']
	s = df[df[target] > threshold].sname

	df = pd.concat([t,s], axis=1)

	df = df.fillna('')

	df = df.groupby('time').agg(lambda x: ''.join(x.astype(str).unique()))

	df = df.reset_index()

	# df = df.drop('time', axis=1)

	df.to_csv('tmp.csv', sep="\t", header=False)




def draw_plot(fig):
	plt.show(block=False)
	return 'Start'


def del_plot(fig):

	# plt.cla(): Axesをクリア
	# plt.clf(): figureをクリア
	# plt.close(): プロットを表示するためにポップアップしたウィンドウをクローズ

	plt.close()