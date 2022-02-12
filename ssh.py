from utils import *



# For interactive work (on ipython) it's easier to work with explicit objects
# instead of contexts.

# calimaps...xxx810calima

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


def get_dataset(start_day, end_day, pollutant):

    print("SSH Tunnel Start")
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
    snames = pd.read_sql(sql='select sname from station_info order by random() limit 6', con=conn)
    # snames...list (['s1','s2',...,'s6'])
    snames = snames['sname'].to_list()

    #会津若松,森合,芳賀,揚土,白河,楢葉#
    # snames = ['07202070','07201200','07203130','07204210','07205050','07542010']
    # snames_str...str ("'s1','s2',...'s6'")
    snames_str = map(lambda x: "'"+ x + "'",snames)
    snames_str = ','.join(snames_str)

    print('selected stations are')
    print(snames,type(snames))


    query=make_query(start_day, end_day, pollutant,snames_str)


    dataset = pd.read_sql(sql=query, con=conn)

    conn.close()

    server.stop()

    return dataset, snames


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
    



def main():

    start_day = '2019-01-01'
    end_day = '2021-01-01'
    pollutant = 'pm25'
    minSup = '100'
    maxPer = '100.0'
    threshold = 10

    original_dataset, snames = get_dataset(start_day,end_day,pollutant)


    create_datasets(original_dataset, snames, 'dateset.csv')


    #ゼロ以下の一時間平均値はゼロに変換される

    data_convert(df = original_dataset, stations = snames, threshold = threshold)


    pattern_mining('tmp.csv', 'pattern_test.csv', minSup, maxPer)





    # df = df.fillna('')

    # df = df.groupby('time').agg(lambda x: ''.join(x.astype(str).unique()))

    # df = df.reset_index()

    # create_datasets(original_dataset,snames,'test.csv')






if __name__=='__main__':
    main()
