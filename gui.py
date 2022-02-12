# ステップ1. インポート
import csv
from random import sample
from threading import Thread
import PySimpleGUI as sg
from utils import *
import time
from mpl_toolkits.mplot3d import Axes3D

def play(filepath, window):

	wav_obj = sa.WaveObject.from_wave_file(filepath)
	play_obj = wav_obj.play()
	
	while True:
		global stop_threads
		if stop_threads is True or play_obj.is_playing() is False:
			play_obj.stop()
			break
    


pollutants = ('pm25', 'so2', 'no', 'no2', 'nox', 'co', 'ox', 'nmhc', 'ch4', 'thc', 'spm', 'sp', 'wd', 'ws', 'temp', 'hum')

modules = ['fc1','fc2','fm2','env1','env2','amp2']

stations = ['s1 ','s2 ','s3 ','s4 ','s5 ','s6 ','Disabled']


today = datetime.datetime.today()


_, _, dsp_info = init_dsp() #initilize dsp and get dsp info

mapping = pd.Series(data='Disabled',index=dsp_info.name.to_list())

# ステップ2. デザインテーマの設定
sg.theme('DarkAmber')

font=('Arial 13')
framesize=(560,150)
toggle=False





frame_1 = sg.Frame('Pattern-mining options', [

    [sg.Column([
        [sg.Text('From',font = font, size=(8,1)),sg.InputText(datetime.date(2019, 1, 1), key='from',font = font, size=(12,1)), sg.CalendarButton('Select',font = font, size=(5,1), target='from', format="%Y-%m-%d", default_date_m_d_y = (1, 1, 2019),)],
        [sg.Text('Pollutant',font = font, size =(8,1)), sg.Combo(pollutants, default_value = pollutants[0],font = font, size=(12,1), key='pollutant', enable_events=True)],
        [sg.Text('minSup',font = font, size=(8,1)), sg.InputText('0.1',font = font, size=(12,1), key='minSup')],
        [sg.Checkbox('stations lock', default=False, key='stations-lock', font=font)]
    ]),

    sg.Column([
        [sg.Text('To',font = font, size=(8,1)), sg.InputText(today.date(), key='to',font = font, size=(12,1)), sg.CalendarButton('Select',font = font, size=(5,1), target='to', format="%Y-%m-%d", default_date_m_d_y = (today.month,today.day,today.year))],
        [sg.Text('Threshold',font = font, size=(8,1)),sg.InputText('30',font = font, size=(12,1), key='threshold')],
        [sg.Text('maxPer',font = font, size=(8,1)), sg.InputText('20.0',font = font, size=(12,1), key='maxPer')],
        [sg.Text('', font=font)]
    ])]
    
    ], size = framesize
)

    

frame_2= sg.Frame('Sonification options', [

    [sg.Column([
        [sg.Text('Select stations to sonify',font=font)],
        
        [sg.Text('Carrier Frequency',size=(18,1),font=font), sg.Combo(stations,font = font, size=(10,1), default_value = stations[6], key=mapping.index[0], enable_events = True)],

        [sg.Text('Modulation Frequency',size=(18,1),font=font), sg.Combo(stations,font = font, size=(10,1), default_value = stations[6], key=mapping.index[1], enable_events = True)],

        [sg.Text('Envelope',size=(18,1),font=font), sg.Combo(stations,font = font, size=(10,1), default_value = stations[6], key=mapping.index[2], enable_events = True)],

        [sg.Text('Sonification rate',font = font, size=(12,1)), sg.InputText('50',font = font, size=(12,1), key='sonification rate'),sg.Text('ms/hour', font=font)],
    ])]
    
    ], size = framesize
)



layout=[
    [sg.Column([
        [frame_1,frame_2],
        [sg.Text("Save to",font = font, size=(8,1)), sg.InputText(font=font), sg.FolderBrowse(key="dir",font=font)],
        [sg.Text("Name",font = font, size=(8,1)), sg.InputText(str(today.date()).replace('-', '_'),font = font, size=(20,1), key='fname')],
        [sg.Output(size=(140,20),font=font)],
        [sg.Button('Find patterns', key='find patterns', font=font),sg.Button('Sonify', key='sonify', font=font),sg.Button('Play', key='play',font=font)]

    ])]
]

window = sg.Window('Sonification', layout, finalize=True)


try:

    while True:
        event, values = window.read()

        folderpath=values['dir']+'/'+values['fname']+'/'+values['fname']
        wavpath=folderpath + '.wav'
        dataset_path=folderpath + '_datasets.csv'
        patterns_path=folderpath + '_patterns.csv'

        if event == sg.WIN_CLOSED:
            break

        if event == 'find patterns' and values['dir'] != '':

            os.makedirs(folderpath,exist_ok=True)

            if values['stations-lock']==False:
                snames = select_stations()
            
            original_dataset= get_dataset(
                start_day = values['from'],
                end_day = values['to'],
                pollutant = values['pollutant'],
                snames = snames
                )

            create_datasets(original_dataset, snames, dataset_path)

            data_convert(df = original_dataset, stations = snames, threshold = float(values['threshold']))

            pattern_mining(patterns_path , values['minSup'], values['maxPer'])



        if event == 'sonify' and os.path.exists(dataset_path):

            for i in range(len(mapping)):
                target_parameter = mapping.index[i]
                mapping[target_parameter] = values[target_parameter]
            
            sonification(
                mapping = mapping,
                sonification_rate = float(values['sonification rate']),
                dir = values['dir'],
                fname = values['fname'])

        if event == 'play':

            for i in range(len(mapping)):
                target_parameter = mapping.index[i]
                mapping[target_parameter] = values[target_parameter]

            if os.path.exists(wavpath) and os.path.exists(dataset_path):

                toggle = not toggle

                if toggle is True:
                    df = pd.read_csv(dataset_path)
                    fig = plt.figure(figsize=(8,8))
                    ax = plt.subplot(projection='3d')

                    c = pd.to_datetime(df['time']).view(int)

                    c  = c.apply(lambda x: x-min(c))

                    print(c)

                    sc = ax.scatter(df[mapping[0]],df[mapping[1]],df[mapping[2]],c=c, s=2,cmap=cm.jet)

                    ax.set_xlabel(mapping[0] + 'fc',color='white')
                    ax.set_ylabel(mapping[1] + 'fm',color='white')
                    ax.set_zlabel(mapping[2] + 'env',color='white') 

                    ax.set_facecolor('black')

                    ax.w_xaxis.set_pane_color((0.4, 0.4, 0.4, 0.6))
                    ax.w_yaxis.set_pane_color((0.4, 0.4, 0.4, 0.6))
                    ax.w_zaxis.set_pane_color((0.4, 0.4, 0.4, 0.6))

                    ax.tick_params(axis='x',colors='white')
                    ax.tick_params(axis='y',colors='white')
                    ax.tick_params(axis='z',colors='white')

                    ax.xaxis._axinfo['tick']['color']='gray'
                    ax.yaxis._axinfo['tick']['color']='gray'
                    ax.zaxis._axinfo['tick']['color']='gray'

                    ax.xaxis.pane.set_edgecolor('grey')
                    ax.yaxis.pane.set_edgecolor('grey')
                    ax.zaxis.pane.set_edgecolor('grey')


                    fig.colorbar(sc,ax=ax, label='time (older -> newer)')

                    draw_plot(fig)
                
                    stop_threads = False
                    t = Thread(target=play, args=(wavpath, window,), daemon=True)
                    t.start()
                
                else:
                    stop_threads = True
                    del_plot(fig)
                    t.join()
            
            
except Exception as e:
    print(e, end="\n\n")
    import traceback
    traceback.print_exc()
    input('Press any key to Continue...')



window.close()
