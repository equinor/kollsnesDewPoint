from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from neqsim.thermo.thermoTools import fluid_df
from neqsim.process import stream, separator
import pandas as pd

class dewPointCalc(BaseModel):
    MEGflow: float=1000.0
    feedGasFlow: float=20.0
    temperature_dpscrubber: float=-25.0
    pressure_dpscrubber: float=-30.0
    
    def calcDewPoint(self):
        feedGas = {
            'ComponentName':  ["nitrogen", "CO2", "methane", "ethane", "propane", "i-butane", "n-butane", "n-pentane", "n-hexane", 'water', 'MEG'], 
            'MolarComposition[-]':  [0.01, 0.02, 0.85, 0.04, 0.01, 0.01, 0.01, 0.001, 0.001, 1.0, 0.01], 
          }
        gascondensateFluid = fluid_df(pd.DataFrame(feedGas))
        gascondensateFluid.autoSelectModel()

        inStream = stream(gascondensateFluid)
        inStream.setPressure(self.pressure_dpscrubber, "bara")
        inStream.setTemperature(self.temperature_dpscrubber, "C")
        #inStream.setFlowRate(self.feedGasFlow, 'MSm3/day')

        dewpSep = separator(inStream)
        inStream.run()
        dewpSep.run()
        return [dewpSep.getGasOutStream().getHydrateEquilibriumTemperature()-273.15]

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