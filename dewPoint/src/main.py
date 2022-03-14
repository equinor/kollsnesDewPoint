from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from neqsim.thermo.thermoTools import fluid_df
from neqsim.process import stream, separator
import pandas as pd
from neqsim.process import expander, mixer, stream, cooler, valve, separator3phase,clearProcess,runProcess, saturator
from neqsim.thermo import phaseenvelope,freeze

class dewPointCalc(BaseModel):
    feedFlowRateTrain1: float=11411.9
    feedPressure: float=89.0
    feedTemperature: float= 5.0
    sep1Pressure: float=85.0
    cooler1T: float=-5.0
    expOutPressure: float=67.0
    glycolFlow: float=10
    expOutTemperature: float=-20.0

    def calcDewPoint(self):
        feedFluid = {'ComponentName':  ['water', 'MEG', "methane", "ethane", "propane","i-butane", "n-butane","i-pentane","n-pentane", "C6", "C7", "C8", "C9", "C10"], 
                'MolarComposition[-]':  [0.0, 0.0, 80.0, 6.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], 
                'MolarMass[kg/mol]': [None,None, None,None,None,None, None,None,None,0.086, 0.093, 0.105, 0.123, 0.150],
                'RelativeDensity[-]': [None,None, None,None,None,None, None,None,None, 0.664, 0.7, 0.75, 0.8, 0.83]
        }

        reservoirFluiddf = pd.DataFrame(feedFluid)
        fluid7 = fluid_df(reservoirFluiddf).autoSelectModel()
        fluid7.setMultiPhaseCheck(True)

        glycolFluid = fluid7.clone()
        glycolFluid.setMolarComposition([0.3, 0.7, 0.0, 0.0,0.0, 0.0,0.0, 0.0,0.0, 0.0,0.0, 0.0,0.0,0.0])

        clearProcess()
        feedStream = stream(fluid7)
        feedStream.setFlowRate(self.feedFlowRateTrain1, 'kg/hr')
        feedStream.setPressure(self.feedPressure, 'barg')
        feedStream.setTemperature(self.feedTemperature, 'C')

        glycolFeedStream = stream(glycolFluid)
        glycolFeedStream.setFlowRate(self.glycolFlow, 'kg/hr')
        glycolFeedStream.setTemperature(self.cooler1T, 'C')
        glycolFeedStream.setPressure(self.sep1Pressure, 'bara')

        slugCatcher = separator(feedStream)

        saturatedGasFromSlugCatcher = saturator(slugCatcher.getGasOutStream(), 'water saturator')

        valve1 = valve(saturatedGasFromSlugCatcher.getOutStream())
        valve1.setOutletPressure(self.sep1Pressure)

        sep1 = separator3phase(valve1.getOutStream())

        cooler1 = cooler(sep1.getGasOutStream())
        cooler1.setOutTemperature(self.cooler1T, 'C')

        sep2 = separator3phase(cooler1.getOutStream())

        mixer1 = mixer()
        mixer1.addStream(sep2.getGasOutStream())
        mixer1.addStream(glycolFeedStream)

        expander1 = cooler(mixer1.getOutStream())
        expander1.setOutTemperature(self.expOutTemperature, 'C')
        expander1.setOutPressure(self.expOutPressure, 'bara')
        #expander1 = expander(mixer1.getOutStream(), self.expOutPressure)

        sep3 = separator3phase(expander1.getOutStream())

        gasToExport = stream(sep3.getGasOutStream())

        runProcess()

        try:
            gasToExport.setPressure(70.0, 'bara')
            gasToExport.setTemperature(-10.0, 'C')
            hydrateT = gasToExport.getHydrateEquilibriumTemperature()-273.15
            hydrateTDewTScrubber = expander1.getOutStream().getHydrateEquilibriumTemperature()-273.15
        except:
            print("Could not find hydrate temperatures - returning -9999")
            hydrateT = -9999
            hydrateTDewTScrubber = -9999

        #MEG freeze chack
        MEGfreezeFluid = expander1.getOutStream().getFluid().clone()
        MEGfreezeFluid.setSolidPhaseCheck('MEG')
        MEGfreezeFluid.setTemperature(-10.0, 'C')
        try:
            freeze(MEGfreezeFluid)
            MEGfrezeT = MEGfreezeFluid.getTemperature('C')
        except:
            print("Could not find freezing point of MEG - returning -9999")
            MEGfrezeT = -9999

        try:
            fluidExport = gasToExport.getFluid().clone()
            fluidExport.removeComponent("water")
            fluidExport.removeComponent("MEG")
            phaseEnvResults = phaseenvelope(fluidExport)
            cricobar = phaseEnvResults.get("cricondenbar")[1]
            cricotherm = phaseEnvResults.get("cricondentherm")[0]-273.15
        except:
            print("Could not calculate phase envelope - returning -9999")
            cricotherm = -9999
        
        return [hydrateT, cricotherm, hydrateTDewTScrubber, MEGfrezeT]

class dewPointResults(BaseModel):
    waterDewPoint: float
    hydrocarbonDewPoint: float
    hydrateTDewTScrubber: float
    MEGfrezeT: float


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

 
@app.post("/kol2/waterDewPoint",response_model=dewPointResults,description="Calculate the water and HC dew point of the gas")
def waterDewPoint(dewPointFunc:dewPointCalc):
    results = dewPointFunc.calcDewPoint()
    results = {
        'waterDewPoint': float(results[0]),
        'hydrocarbonDewPoint':float(results[1]),
        'hydrateTDewTScrubber':float(results[2]),
        'MEGfrezeT':float(results[3])
    }
    return results