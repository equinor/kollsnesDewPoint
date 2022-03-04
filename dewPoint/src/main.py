from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from neqsim.thermo.thermoTools import fluid_df
from neqsim.process import stream, separator
import pandas as pd
from neqsim.process import expander, mixer, stream, cooler, valve, separator3phase,clearProcess,runProcess

class dewPointCalc(BaseModel):
    feedFlowRateTrain1: float=11411.9
    feedPressure: float=89.0
    feedTemperature: float= 5.0
    sep1Pressure: float=85.0
    cooler1T: float=-5.0
    expOutPressure: float=67.0
    glycolFlow: float=10

    def calcDewPoint(self):
        feedFluid = {'ComponentName':  ['water', 'MEG', "methane", "ethane", "C6", "C7"], 
                'MolarComposition[-]':  [1.0, 0.0, 0.5, 0.1,0.1, 0.3], 
                'MolarMass[kg/mol]': [None,None, None,None, 0.091, 0.19],
                'RelativeDensity[-]': [None,None,None,None, 0.7, 0.86 ]
        }

        reservoirFluiddf = pd.DataFrame(feedFluid)
        fluid7 = fluid_df(reservoirFluiddf)

        glycolFluid = fluid7.clone()
        glycolFluid.setMolarComposition([0.0, 1.0, 0.0, 0.0,0.0, 0.0])

        clearProcess()
        feedStream = stream(fluid7)
        feedStream.setFlowRate(self.feedFlowRateTrain1, 'kg/hr')
        feedStream.setPressure(self.feedPressure, 'barg')
        feedStream.setTemperature(self.feedTemperature, 'C')

        glycolFeedStream = stream(glycolFluid)
        glycolFeedStream.setFlowRate(self.glycolFlow, 'kg/hr')
        glycolFeedStream.setTemperature(self.feedTemperature, 'C')
        glycolFeedStream.setPressure(self.feedPressure, 'barg')

        slugCatcher = separator3phase(feedStream)

        gasFromSlugCatcher = stream(slugCatcher.getGasOutStream())

        valve1 = valve(gasFromSlugCatcher)
        valve1.setOutletPressure(self.sep1Pressure)

        sep1 = separator3phase(valve1.getOutStream())

        cooler1 = cooler(sep1.getGasOutStream())
        cooler1.setOutTemperature(self.cooler1T, 'C')

        sep2 = separator3phase(cooler1.getOutStream())

        mixer1 = mixer()
        mixer1.addStream(sep2.getGasOutStream())
        mixer1.addStream(glycolFeedStream)

        expander1 = expander(mixer1.getOutStream(), self.expOutPressure)

        sep3 = separator3phase(expander1.getOutStream())

        gasToExport = stream(sep3.getGasOutStream())

        runProcess()

        gasToExport.setPressure(70.0, 'bara')

        return [gasToExport.getHydrateEquilibriumTemperature()-273.15]

class dewPointResults(BaseModel):
    waterDewPoint: float


app = FastAPI()

@app.get("/")
def read_root():
    html_content = """
    <html>
        <head>
            <title>NeqSim Live Dew Point Calculations for Kollsnes</title>
        </head>        <body>
            <h1>NeqSim Live Dew Point Calculations for Kollsnes</h1>
            <a href="/docs">API documentation and testing</a><br>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

 
@app.post("/kol2/waterDewPoint",response_model=dewPointResults,description="Calculate the water dew point of the gas")
def waterDewPoint(dewPointFunc:dewPointCalc):
    results = dewPointFunc.calcDewPoint()
    results = {
        'waterDewPoint': float(results[0])
    }
    return results