from collections import defaultdict

class MessageQueue:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def publish(self, topic, data):
        for callback in self.subscribers[topic]:
            callback(data)

    def subscribe(self, topic, callback):
        self.subscribers[topic].append(callback)

mq = MessageQueue()