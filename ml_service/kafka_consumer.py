import aiokafka
import asyncio
from datetime import datetime, timedelta

async def consume_from_kafka(timeout: int = 5):
    consumer = aiokafka.AIOKafkaConsumer(
        'raw_reviews',
        bootstrap_servers='kafka1:29092',
        group_id="ml-service-consumer"
    )
    
    messages = []
    start_time = datetime.utcnow()

    await consumer.start()

    try:
        print("Consumer started...")
        
        while True:
            if (datetime.utcnow() - start_time) >= timedelta(seconds=timeout):
                break

            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=timeout)
            except asyncio.TimeoutError:
                continue

            if msg:
                messages.append(msg.value.decode())

    except Exception as e:
        print(f"Error while consuming messages: {e}")
    
    finally:
        await consumer.stop()

    print(f"Messages collected in {timeout} seconds: {len(messages)}")
    return messages
