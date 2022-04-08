from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from neqsim.thermo.thermoTools import fluid_df
from neqsim.process import stream, separator
import pandas as pd
from neqsim.process import expander, mixer, stream, cooler, valve, separator3phase,clearProcess,runProcess, saturator, heater, splitter
from neqsim.thermo import phaseenvelope,freeze

class dewPointCalc(BaseModel):
    feedFlowRateTrain1: float= Field(
        20.83, gt=-100, lt= 100.0, description="feed flow rate in unit MSm3/day"
    )
    feedPressure: float= Field(
        91.96, gt=0, lt= 1000.0, description="feed pressure in unit bara"
    )
    feedTemperature: float= Field(
        6.0, gt=-100, lt= 100.0, description="feed temperature in unit deg C"
    )
    sep1Pressure: float= Field(
        87.94, gt=0, lt= 1000.0, description="separator pressure in unit bara"
    )
    cooler1T: float= Field(
        13.0, gt=-100, lt= 100.0, description="cooler out temperature in unit deg C"
    )
    expOutPressure: float= Field(
        68.18, gt=0, lt= 1000.0, description="expander out pressure in unit bara"
    )
    glycolFlow: float= Field(
        0.128, gt=0, lt= 100.0, description="glycol flow rate in unit ???"
    )
    expOutTemperature: float= Field(
        -20.0, gt=-100, lt= 100.0, description="expander out temperature in unit deg C"
    )

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

        feedFluidGvitB = {'ComponentName':  ['water', 'MEG', "nitrogen","CO2","methane", "ethane", "propane","i-butane", "n-butane","i-pentane","n-pentane", "C6", "C7", "C8", "C9", "C10","C11","C12","C13","C14","C15","C16","C17","C18"], 
                'MolarComposition[-]':  [0.0, 0.0, 1.642125, 0.562613, 92.57445, 3.573913,0.0374963,0,0.00,0.00,0.00,0.0,0.0,0.0,0.0,0.0,.0,0.0,0.00,0.0,0.0,0.0,0.0,0.0], 
                'MolarMass[kg/mol]': [None,None, None,None,None,None,None,None, None,None,None,0.08306162,0.08879617,0.103527,0.119918,0.1345865,0.1475065,0.1618353,0.175582,0.1913808,0.2065661,0.2215028,0.2367315,0.2790842],
                'RelativeDensity[-]': [None,None, None,None,None,None,None,None, None,None,None, 0.67666,0.753736,0.76288,0.782873,0.803976,0.816404,0.83019,0.840552,0.85174,0.861973,0.872268,0.880661,0.90976]
        }

        reservoirFluiddfGVitB = pd.DataFrame(feedFluidGvitB)
        fluid7KvitB = fluid_df(reservoirFluiddf).autoSelectModel()
        fluid7KvitB.setMultiPhaseCheck(True)
        
        clearProcess()
        feedStream = stream(fluid7)
        feedStream.setFlowRate(self.feedFlowRateTrain1, 'kg/hr')
        feedStream.setPressure(self.feedPressure, 'barg')
        feedStream.setTemperature(self.feedTemperature, 'C')

        slugCatcher = separator(feedStream)

        saturatedGasFromSlugCatcher = saturator(slugCatcher.getGasOutStream(), 'water saturator')

        total = self.feedFlowRateTrain1+self.feedFlowRateTrain2+self.feedFlowRateTrain3
        splitFactor = [self.feedFlowRateTrain1/total, self.feedFlowRateTrain2/total, self.feedFlowRateTrain3/total]
        spliterFeed = splitter(saturatedGasFromSlugCatcher, splitFactor)

        feedTrain1 = spliterFeed.getSplitStream(0)
        feedTrain2 = spliterFeed.getSplitStream(1)
        feedTrain3 = spliterFeed.getSplitStream(2)


        # Train 1
        valve1_train1 = valve(feedTrain1)
        valve1_train1.setOutletPressure(self.sep1Pressure_train1, "bara")

        sep1_train1 = separator3phase(valve1_train1.getOutStream())

        cooler1_train1 = cooler(sep1_train1.getGasOutStream())
        cooler1_train1.setOutTemperature(self.cooler1T_train1, 'C')

        sep2_train1 = separator3phase(cooler1_train1.getOutStream())

        glycolFeedStream_train1 = stream(glycolFluid)
        glycolFeedStream_train1.setFlowRate(self.glycolFlow_train1, 'kg/hr')
        glycolFeedStream_train1.setTemperature(self.cooler1T_train1, 'C')
        glycolFeedStream_train1.setPressure(self.sep1Pressure_train1, 'bara')

        mixer1_train1 = mixer()
        mixer1_train1.addStream(sep2_train1.getGasOutStream())
        mixer1_train1.addStream(glycolFeedStream_train1)

        expander1_train1 = cooler(mixer1_train1.getOutStream())
        expander1_train1.setOutTemperature(self.expOutTemperature_train1, 'C')
        expander1_train1.setOutPressure(self.expOutPressure_train1, 'bara')
        #expander1 = expander(mixer1.getOutStream(), self.expOutPressure)

        sep3_train1 = separator3phase(expander1_train1.getOutStream())

        gasToExport_train1 = stream(sep3_train1.getGasOutStream())

        gasToManifoldTPsetter_train1 = heater("TP of gas to absorber", gasToExport_train1)
        gasToManifoldTPsetter_train1.setOutPressure(75.05, "bara")
        gasToManifoldTPsetter_train1.setOutTemperature(55.9, "C")


        # Train 2
        valve1_train2 = valve(feedTrain2)
        valve1_train2.setOutletPressure(self.sep1Pressure_train2, "bara")

        sep1_train2 = separator3phase(valve1_train2.getOutStream())

        cooler1_train2 = cooler(sep1_train2.getGasOutStream())
        cooler1_train2.setOutTemperature(self.cooler1T_train2, 'C')

        sep2_train2 = separator3phase(cooler1_train2.getOutStream())

        glycolFeedStream_train1 = stream(glycolFluid)
        glycolFeedStream_train1.setFlowRate(self.glycolFlow_train1, 'kg/hr')
        glycolFeedStream_train1.setTemperature(self.cooler1T_train1, 'C')
        glycolFeedStream_train1.setPressure(self.sep1Pressure_train1, 'bara')

        mixer1_train1 = mixer()
        mixer1_train1.addStream(sep2_train1.getGasOutStream())
        mixer1_train1.addStream(glycolFeedStream_train1)

        expander1_train1 = cooler(mixer1_train1.getOutStream())
        expander1_train1.setOutTemperature(self.expOutTemperature_train1, 'C')
        expander1_train1.setOutPressure(self.expOutPressure_train1, 'bara')
        #expander1 = expander(mixer1.getOutStream(), self.expOutPressure)

        sep3_train1 = separator3phase(expander1_train1.getOutStream())

        gasToExport_train2 = stream(sep3_train1.getGasOutStream())

        gasToManifoldTPsetter_train2 = heater("TP of gas to absorber", gasToExport_train1)
        gasToManifoldTPsetter_train2.setOutPressure(75.05, "bara")
        gasToManifoldTPsetter_train2.setOutTemperature(55.9, "C")


        # Train 3    ...... to be updated
        valve1_train3 = valve(feedTrain3)
        valve1_train3.setOutletPressure(self.sep1Pressure_train3, "bara")

        sep1_train3 = separator3phase(valve1_train2.getOutStream())

        cooler1_train2 = cooler(sep1_train2.getGasOutStream())
        cooler1_train2.setOutTemperature(self.cooler1T_train2, 'C')

        sep2_train2 = separator3phase(cooler1_train2.getOutStream())

        glycolFeedStream_train1 = stream(glycolFluid)
        glycolFeedStream_train1.setFlowRate(self.glycolFlow_train1, 'kg/hr')
        glycolFeedStream_train1.setTemperature(self.cooler1T_train1, 'C')
        glycolFeedStream_train1.setPressure(self.sep1Pressure_train1, 'bara')

        mixer1_train1 = mixer()
        mixer1_train1.addStream(sep2_train1.getGasOutStream())
        mixer1_train1.addStream(glycolFeedStream_train1)

        expander1_train1 = cooler(mixer1_train1.getOutStream())
        expander1_train1.setOutTemperature(self.expOutTemperature_train1, 'C')
        expander1_train1.setOutPressure(self.expOutPressure_train1, 'bara')
        #expander1 = expander(mixer1.getOutStream(), self.expOutPressure)

        sep3_train1 = separator3phase(expander1_train1.getOutStream())

        gasToExport_train3 = stream(sep3_train1.getGasOutStream())

        gasToManifoldTPsetter_train3 = heater("TP of gas to absorber", gasToExport_train1)
        gasToManifoldTPsetter_train3.setOutPressure(75.05, "bara")
        gasToManifoldTPsetter_train3.setOutTemperature(55.9, "C")

        KvitBfeedStream = stream(fluid7KvitB)
        KvitBfeedStream.setFlowRate(self.feedFlowRateKivtB, 'kg/hr')
        KvitBfeedStream.setPressure(self.feedPressureKvitB, 'barg')
        KvitBfeedStream.setTemperature(self.feedTemperatureKvitB, 'C')


        mixerAllGasses = mixer('gas mixer')
        mixerAllGasses.addStream(gasToManifoldTPsetter_train1)
        mixerAllGasses.addStream(gasToManifoldTPsetter_train2)
        mixerAllGasses.addStream(gasToManifoldTPsetter_train3)
        mixerAllGasses.addStream(KvitBfeedStream)

        totalExportGas = self.expFlowRatePipe1+ self.expFlowRatePipe2+self.expFlowRatePipe3+self.expFlowRatePipe4
        splitFactorExpGas = [self.expFlowRatePipe1/totalExportGas, self.expFlowRatePipe2/totalExportGas, self.expFlowRatePipe3/totalExportGas,self.expFlowRatePipe4/totalExportGas]
        splitterToExport = splitter(mixerAllGasses, splitFactorExpGas)

        exportGasPipe1 = splitterToExport.getSplitStream(0)
        exportGasPipe2 = splitterToExport.getSplitStream(1)
        exportGasPipe3 = splitterToExport.getSplitStream(2)
        exportGasPipe4 = splitterToExport.getSplitStream(3)

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


        try:
            fluidExport1 = exportGasPipe1.getFluid().clone()
            fluidExport1.removeComponent("water")
            fluidExport1.removeComponent("MEG")
            phaseEnvResults1 = phaseenvelope(fluidExport1)
            cricobar1 = phaseEnvResults1.get("cricondenbar")[1]
            cricoTExpotGas1 = phaseEnvResults1.get("cricondentherm")[0]-273.15
            if(cricoTExpotGas1<-100.0 or cricotherm1>50.0):
                cricoTExpotGas1=-9999
        except:
            print("Could not calculate phase envelope - returning -9999")
            cricoTExpotGas1 = -9999

        try:
            fluidExport2 = exportGasPipe2.getFluid().clone()
            fluidExport2.removeComponent("water")
            fluidExport2.removeComponent("MEG")
            phaseEnvResults2 = phaseenvelope(fluidExport2)
            cricobar2 = phaseEnvResults1.get("cricondenbar")[1]
            cricoTExpotGas2 = phaseEnvResults2.get("cricondentherm")[0]-273.15
            if(cricoTExpotGas2<-100.0 or cricotherm2>50.0):
                cricoTExpotGas2=-9999
        except:
            print("Could not calculate phase envelope - returning -9999")
            cricoTExpotGas2 = -9999
        
        try:
            fluidExport3 = exportGasPipe2.getFluid().clone()
            fluidExport3.removeComponent("water")
            fluidExport3.removeComponent("MEG")
            phaseEnvResults3 = phaseenvelope(fluidExport2)
            cricobar2 = phaseEnvResults1.get("cricondenbar")[1]
            cricoTExpotGas3 = phaseEnvResults2.get("cricondentherm")[0]-273.15
            if(cricoTExpotGas3<-100.0 or cricotherm3>50.0):
                cricoTExpotGas3=-9999
        except:
            print("Could not calculate phase envelope - returning -9999")
            cricoTExpotGas3 = -9999

        try:
            fluidExport4 = exportGasPipe4.getFluid().clone()
            fluidExport4.removeComponent("water")
            fluidExport4.removeComponent("MEG")
            phaseEnvResults4 = phaseenvelope(fluidExport4)
            cricobar4 = phaseEnvResults1.get("cricondenbar")[1]
            cricoTExpotGas4 = phaseEnvResults2.get("cricondentherm")[0]-273.15
            if(cricoTExpotGas4<-100.0 or cricotherm4>50.0):
                cricoTExpotGas4=-9999
        except:
            print("Could not calculate phase envelope - returning -9999")
            cricoTExpotGas4 = -9999


        return [hydrateT, cricotherm, hydrateTDewTScrubber, MEGfrezeT, cricoTExpotGas1,cricoTExpotGas2,cricoTExpotGas3,cricoTExpotGas4]

class dewPointResults(BaseModel):
    waterDewPoint: float= Field(
        None, description="water dew point temperature [C]"
    )
    hydrocarbonDewPoint: float= Field(
        None, description="hydrocarbon dew point temperature [C]"
    )
    hydrateTDewTScrubber: float= Field(
        None, description="hydrate temperature in dew point scrubber [C]"
    )
    MEGfrezeT: float= Field(
        None, description="Solid formation temperature of MEG in dew point scrubber [C]"
    )


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
        'MEGfrezeT':float(results[3]),
        'cricoTExpotGas1':float(results[4]),
        'cricoTExpotGas2':float(results[5]),
        'cricoTExpotGas3':float(results[6]),
        'cricoTExpotGas4':float(results[7])
    }
    return results