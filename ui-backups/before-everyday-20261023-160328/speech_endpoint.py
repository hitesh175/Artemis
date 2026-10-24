"""Small RMS-based turn endpoint; consumes existing audio without another stream."""
class SpeechEndpoint:
    def __init__(self, pause=1.2, wait=10.0):
        self.pause=pause
        self.wait=wait
        self.elapsed=0.0
        self.voiced=0.0
        self.silence=0.0
        self.noise=.002
        self.started=False

    def feed(self, rms, seconds):
        self.elapsed+=seconds
        threshold=max(.009,min(.035,self.noise*2.8))
        if rms>=threshold:
            self.voiced+=seconds
            self.silence=0.0
            if self.voiced>=.25:
                self.started=True
        else:
            if not self.started:
                self.noise=self.noise*.95+rms*.05
                self.voiced=max(0.,self.voiced-seconds*.5)
            self.silence+=seconds
        if self.started and self.silence>=self.pause:
            return 'done'
        if not self.started and self.elapsed>=self.wait:
            return 'timeout'
        return 'continue'
