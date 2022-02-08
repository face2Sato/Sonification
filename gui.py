# ステップ1. インポート
import csv
from random import sample
from threading import Thread
import PySimpleGUI as sg
from utils import *
import time

def play(filepath, window):

	wav_obj = sa.WaveObject.from_wave_file(filepath)
	play_obj = wav_obj.play()
	
	while True:
		global stop_threads
		if stop_threads is True or play_obj.is_playing() is False:
			play_obj.stop()
			break
    


pollutants = ('pm25', 'so2', 'no', 'no2', 'nox', 'co', 'ox', 'nmhc', 'ch4', 'thc', 'spm', 'sp', 'wd', 'ws')

modules = ['fc1','fc2','fm2','env1','env2','amp2']

stations = ['s1 ','s2 ','s3 ','s4 ','s5 ','s6 ','Disabled']


today = datetime.datetime.today()


_, _, dsp_info = init_dsp() #initilize dsp and get dsp info

mapping = pd.Series(data='Disabled',index=dsp_info.name.to_list())

# ステップ2. デザインテーマの設定
sg.theme('DarkAmber')

framesize=(500,130)
toggle=False





frame_1 = sg.Frame('Pattern-mining options', [

    [sg.Column([
        [sg.Text('From', size=(8,1)),sg.InputText(datetime.date(2019, 1, 1), key='from', size=(12,1)), sg.CalendarButton('Select', size=(5,1), target='from', format="%Y-%m-%d", default_date_m_d_y = (1, 1, 2019),)],
        [sg.Text('Pollutant', size =(8,1)), sg.Combo(pollutants, default_value = pollutants[0], size=(12,1), key='pollutant', enable_events=True)],
        [sg.Text('minSup', size=(8,1)), sg.InputText('100', size=(12,1), key='minSup')]
    
    ]),

    sg.Column([
        [sg.Text('To', size=(8,1)), sg.InputText(today.date(), key='to', size=(12,1)), sg.CalendarButton('Select', size=(5,1), target='to', format="%Y-%m-%d", default_date_m_d_y = (today.month,today.day,today.year))],
        [sg.Text('Threshold', size=(8,1)),sg.InputText('30', size=(12,1), key='threshold')],
        [sg.Text('maxPer', size=(8,1)), sg.InputText('10000', size=(12,1), key='maxPer')]
    ])]
    
    ], size = framesize
)

    

frame_2= sg.Frame('Sonification options', [

    [sg.Column([
        [sg.Text('Select stations to sonify')],
        

        [sg.Text('Carrier Frequency',size=(18,1)), sg.Combo(stations, size=(10,1), default_value = stations[6], key=mapping.index[0], enable_events = True)],

        [sg.Text('Modulation Frequency',size=(18,1)), sg.Combo(stations, size=(10,1), default_value = stations[6], key=mapping.index[1], enable_events = True)],

        [sg.Text('Envelope',size=(18,1)), sg.Combo(stations, size=(10,1), default_value = stations[6], key=mapping.index[2], enable_events = True)],

        [sg.Text('Sonification rate', size=(12,1)), sg.InputText('50', size=(12,1), key='sonification rate'),sg.Text('ms/hour')],
    ])]
    
    ], size = framesize
)



layout=[
    [sg.Column([
        [frame_1,frame_2],
        [sg.Text("Save to", size=(8,1)), sg.InputText(), sg.FolderBrowse(key="dir")],
        [sg.Text("Name", size=(8,1)), sg.InputText(str(today.date()).replace('-', '_'), size=(20,1), key='fname')],
        [sg.Output(size=(165,20))],
        [sg.Button('Find patterns', key='find patterns'),sg.Button('Sonify', key='sonify'),sg.Button('Play', key='play')]

    ])]
]

# ステップ4. ウィンドウの生成
window = sg.Window('Sonification', layout)

# ステップ5. イベントループ
try:

    while True:
        event, values = window.read()

        folderpath=values['dir']+'/'+values['fname']+'/'+values['fname']
        wavpath=folderpath + '.wav'
        csvpath=folderpath + '_datasets.csv'

        if event == sg.WIN_CLOSED: #ウィンドウのXボタンを押したときの処理
            break

        if event == 'find patterns' and values['dir'] != '':
            # print(values['dir'],type(values['dir']))
            # print(values['fname'],type(values['fname']))
            ssh(
                start_day = values['from'],
                end_day = values['to'],
                target = values['pollutant'],
                threshold = values['threshold'],
                minSup = values['minSup'],
                maxPer = values['maxPer'],
                save_dir = values['dir'],
                save_fname = values['fname'])


        if event == 'sonify' and os.path.exists(csvpath):

            for i in range(len(mapping)):
                target_parameter = mapping.index[i]
                mapping[target_parameter] = values[target_parameter]
            
            sonification(
                mapping = mapping,
                sonification_rate = float(values['sonification rate']),
                dir = values['dir'],
                fname = values['fname'])

        if event == 'play':

            if os.path.exists(wavpath) and os.path.exists(csvpath):

                toggle = not toggle

                if toggle is True:
                    df = pd.read_csv(csvpath)
                    fig_ = df.plot('time',subplots=True,sharex=True, sharey=True, rot=20, figsize=(8,8),fontsize=7)
                    print(draw_plot(fig_))

                    stop_threads = False
                    t = Thread(target=play, args=(wavpath, window,), daemon=True)
                    t.start()
                
                else:
                    stop_threads = True
                    t.join()
                    del_plot(fig_)
            

        # if event == 'display':
            # filepath=values['dir']+'/'+values['fname']+'/'+values['fname']
            # csvpath=filepath + '_datasets.csv'

            # toggle = not toggle

            # if toggle is True:
            #     df = pd.read_csv(csvpath)
            #     fig_ = df.plot('time',subplots=True,sharex=True, sharey=True, rot=20, figsize=(10,8),fontsize=7)
            #     draw_plot(fig_)

            # else:
            # del_plot(fig_)
            
except Exception as e:
    print(e, end="\n\n")
    import traceback
    traceback.print_exc()
    input('Press any key to Continue...')



window.close()
