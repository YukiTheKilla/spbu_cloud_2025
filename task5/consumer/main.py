import pika, pickle, time
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def get_conn():
    while True:
        try:
            return pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq',port=5672))
        except:
            time.sleep(2)

conn = get_conn()
ch = conn.channel()
ch.exchange_declare(exchange='dlx',exchange_type='direct')
ch.queue_declare(queue='dlq',durable=True)
ch.queue_declare(queue='task',durable=True,arguments={"x-dead-letter-exchange":"dlx","x-dead-letter-routing-key":"dlq"})
ch.queue_declare(queue='result',durable=True)

def on_msg(ch,method,props,body):
    data = pickle.loads(body)
    df = data['df']
    if isinstance(df,str):
        ch.basic_reject(delivery_tag=method.delivery_tag,requeue=False)
        return
    X = df[['x']].values
    y = df['y'].values
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=0.2)
    m = LinearRegression()
    m.fit(Xtr,ytr)
    yp = m.predict(Xte)
    metrics = [float(mean_absolute_error(yte,yp)),float(mean_squared_error(yte,yp)),float(r2_score(yte,yp))]
    out = pickle.dumps({'corr_id':data['corr_id'],'metrics':metrics})
    ch.basic_publish(exchange='',routing_key='result',body=out)
    ch.basic_ack(delivery_tag=method.delivery_tag)

ch.basic_consume(queue='task',on_message_callback=on_msg)
ch.start_consuming()
