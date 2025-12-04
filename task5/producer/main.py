import pika, pickle, pandas as pd, numpy as np, uuid, time

def get_conn():
    while True:
        try:
            return pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq',port=5672))
        except:
            time.sleep(2)

series = 0
while True:
    series += 1
    conn = get_conn()
    ch = conn.channel()
    ch.exchange_declare(exchange='dlx',exchange_type='direct')
    ch.queue_declare(queue='dlq',durable=True)
    ch.queue_bind(exchange='dlx',queue='dlq',routing_key='dlq')
    ch.queue_declare(queue='task',durable=True,arguments={"x-dead-letter-exchange":"dlx","x-dead-letter-routing-key":"dlq"})
    ch.queue_declare(queue='result',durable=True)
    bad = (series % 3 == 0)
    for _ in range(5):
        cid = str(uuid.uuid4())
        if bad:
            body = pickle.dumps({"corr_id":cid,"df":"invalid"})
        else:
            df = pd.DataFrame({'x':np.random.rand(200),'y':np.random.rand(200)})
            body = pickle.dumps({"corr_id":cid,"df":df})
        ch.basic_publish(exchange='',routing_key='task',body=body)
    conn.close()
    time.sleep(10)
