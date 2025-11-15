import aiokafka
import json

async def send_to_kafka(topic: str, message: dict):
    async with aiokafka.AIOKafkaProducer(
        bootstrap_servers='kafka1:29092'
    ) as producer:
        try:
            message_bytes = json.dumps(message).encode('utf-8')
            
            await producer.send_and_wait(topic, message_bytes)
            print(f"Message sent to topic {topic}: {message}")
        except Exception as e:
            print(f"Error sending message to Kafka: {e}")
