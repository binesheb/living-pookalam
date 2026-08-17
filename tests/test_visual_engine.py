from app.visuals.engine import Interaction, VisualEngine

class Dummy:
    def circle(self,*a,**k): pass
    def ellipse(self,*a,**k): pass
    def line(self,*a,**k): pass
    def polygon(self,*a,**k): pass

def test_engine_updates_and_renders():
    e=VisualEngine(seed=1)
    e.update(0.016, Interaction(.5,.5,.8,True))
    e.render(Dummy(),1920,1080,interaction=Interaction(.5,.5,.8,True))

def test_effect_switches():
    e=VisualEngine()
    e.set_all(False)
    assert not any(e.effects.values())
    e.set_effect("lotus_bloom", True)
    assert e.effects["lotus_bloom"]
