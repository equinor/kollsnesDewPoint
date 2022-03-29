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
        feedFluid = {'ComponentName':  ['water', 'MEG', "nitrogen","CO2","methane", "ethane", "propane","i-butane", "n-butane","i-pentane","n-pentane", "C6", "C7", "C8", "C9", "C10","C11","C12","C13","C14","C15","C16","C17","C18"], 
                'MolarComposition[-]':  [0.0, 0.0, 1.642125, 0.562613, 92.57445, 3.573913,0.374963,0.330001,0.039872,0.059775,0.012948,0.103441,0.210647,0.139683,0.050225,0.027926,.017926,0.01137,0.007099,0.004257,0.002424,0.00128,0.000612,0.000258], 
                'MolarMass[kg/mol]': [None,None, None,None,None,None,None,None, None,None,None,0.08306162,0.08879617,0.103527,0.119918,0.1345865,0.1475065,0.1618353,0.175582,0.1913808,0.2065661,0.2215028,0.2367315,0.2790842],
                'RelativeDensity[-]': [None,None, None,None,None,None,None,None, None,None,None, 0.67666,0.753736,0.76288,0.782873,0.803976,0.816404,0.83019,0.840552,0.85174,0.861973,0.872268,0.880661,0.90976]
        }

        reservoirFluiddf = pd.DataFrame(feedFluid)
        fluid7 = fluid_df(reservoirFluiddf).autoSelectModel()
        fluid7.setMultiPhaseCheck(True)

        glycolFluid = fluid7.clone()
        glycolFluid.setMolarComposition([0.3, 0.7, 0.0, 0.0,0.0, 0.0,0.0, 0.0,0.0, 0.0,0.0,0.0,0.0, 0.0,0.0,0.0,0.0, 0.0,0.0,0.0,0.0, 0.0,0.0,0.0])

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
        valve1.setOutletPressure(self.sep1Pressure, "bara")

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
            gasToExportClone = gasToExport.clone()
            gasToExportClone.setPressure(70.0, 'bara')
            gasToExportClone.setTemperature(-10.0, 'C')
            hydrateT = gasToExportClone.getHydrateEquilibriumTemperature()-273.15
            expander1OutClone = expander1.getOutStream().clone()
            hydrateTDewTScrubber = expander1OutClone.getHydrateEquilibriumTemperature()-273.15
            if(hydrateT<-100.0):
                hydrateT=-9999
            if(hydrateTDewTScrubber<-100.0):
                hydrateTDewTScrubber=-9999
        except:
            print("Could not find hydrate temperatures - returning -9999")
            hydrateT = -9999
            hydrateTDewTScrubber = -9999

        #MEG freeze check
        MEGfreezeFluid = expander1.getOutStream().getFluid().clone() 
        MEGfreezeFluid.setSolidPhaseCheck('MEG')
        MEGfreezeFluid.setTemperature(-10.0, 'C')
        try:
            freeze(MEGfreezeFluid)
            MEGfrezeT = MEGfreezeFluid.getTemperature('C')
            if(MEGfrezeT<-100.0):
                MEGfrezeT=-9999
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
            if(cricotherm<-100.0 or cricotherm>50.0):
                cricotherm=-9999
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