import numpy as np
from supportFunctions import weightsFromFraction, getDephasingTimes, weightedCrbTwoEchoes
import bokeh
from bokeh.plotting import figure, output_file, output_notebook, show
from bokeh.models import ColumnDataSource, CustomJS, Title, HoverTool, Span
from bokeh.palettes import viridis
from bokeh.layouts import column
from bokeh.models.widgets import Slider

numFrac = 64
numPF = 64
W = weightsFromFraction(np.linspace(0,1,numFrac))

#output_file()

p1 = figure(height=200, width=200, toolbar_location=None, title='Weights')

l = p1.line(np.linspace(0,1,numFrac), W[1], legend="w1", color='navy')
l = p1.line(np.linspace(0,1,numFrac), W[1], legend="w2", color='chocolate')

ta = 3.6e-3 # Available acquisition time
B0 = 3 # Tesla

acquistionTimes = np.arange(start=2.3, stop=4.6, step=.1)
numTa = len(acquistionTimes)
partialFourierFactors = np.linspace(start=0.5, stop=1, num=numPF)
dephasingTimes = np.empty(shape=(numPF,numFrac,numTa,2), dtype=np.float32)
firstEchoFractions = np.linspace(start=0, stop=1, num=numFrac)
CRB = np.empty(shape=(numPF,numFrac,numTa,2), dtype=np.float32) # [W, F] at 0% fat fraction

for nt, ta in enumerate(acquistionTimes):
    for nPF,PF in enumerate(partialFourierFactors):
        for nf, f in enumerate(firstEchoFractions):
            dephasingTimes[nPF, nf, nt, :] = getDephasingTimes(ta/1e3, PF, f)
            weights = weightsFromFraction(f);
            #print(dephasingTimes[nPF, nf, nt, :])
            CRB[nPF, nf, nt, :] = weightedCrbTwoEchoes(B0, dephasingTimes[nPF, nf, nt, :], weights)
    print(nPF)


p2 = figure(height=350, width=700,tools="hover", toolbar_location=None, title='Search space')
CDSimages = [ColumnDataSource({'imageData': [CRB[:,:,-1,0]]}),
             ColumnDataSource({'imageData': [CRB[:,:,-1,1]]})]
p2.image(image='imageData', x=0,       y=0, dw=numFrac, dh=numPF, palette=viridis(100), source=CDSimages[0])
p2.image(image='imageData', x=numFrac, y=0, dw=numFrac, dh=numPF, palette=viridis(100), source=CDSimages[1])
p2.x_range.range_padding = p2.y_range.range_padding = 0
spans = [Span(location=-1, dimension='height', line_color='navy', line_dash='dashed'),
         Span(location=-1, dimension='height', line_color='chocolate', line_dash='dashed')]
pGrad = figure(height=350, width=700, toolbar_location=None, title='Gradients')
pGrad.add_layout(spans[0])
pGrad.add_layout(spans[1])
CDSFirst = ColumnDataSource({'t': [0, 0, .5, .5], 'amp': [0, 1, 1, 0]})
CDSSecond = ColumnDataSource({'t': [.5, .5, 1, 1], 'amp': [0, -1, -1, 0]})
pGrad.line(x='t', y='amp', color='navy', source=CDSFirst)
pGrad.line(x='t', y='amp', color='chocolate', source=CDSSecond)


slider = Slider(start=np.min(acquistionTimes),
                end=np.max(acquistionTimes),
                value=np.max(acquistionTimes),
                step=acquistionTimes[1]-acquistionTimes[0],
                title="Available acquisition time [ms]")

# dephasingTimes[PfIdx][fIdx][0][0];
hoverCallback = CustomJS(
                        args={
                         'dephasingTimes': dephasingTimes,
                         'firstEchoFractions': firstEchoFractions,
                         'partialFourierFactors': partialFourierFactors,
                         'spans': spans,
                         'first': CDSFirst,
                         'slider': slider,
                         'second': CDSSecond,},
                        code="""
                        if ( isFinite(cb_data['geometry']['x']) && isFinite(cb_data['geometry']['y']) ) {
                            let ta = slider.value / 1000.0
                            let fIdx = Math.floor(cb_data["geometry"]['x']) % firstEchoFractions.length;
                            let pfIdx = Math.floor(cb_data["geometry"]['y']);
                            first.data.t[2] = first.data.t[3] = ta*firstEchoFractions[fIdx];
                            second.data.t[0] = second.data.t[1] = ta*firstEchoFractions[fIdx];
                            second.data.t[2] = second.data.t[3] = ta;
                            first.data.amp[1] = first.data.amp[2] = partialFourierFactors[pfIdx] / firstEchoFractions[fIdx];
                            second.data.amp[1] = second.data.amp[2] = - partialFourierFactors[pfIdx] / (1 - firstEchoFractions[fIdx]);
                            spans[0].location = ta/2.0 + dephasingTimes[pfIdx][fIdx][0][0];
                            spans[1].location = ta/2.0 + dephasingTimes[pfIdx][fIdx][0][1];
                            
                            spans[0].change.emit()
                            spans[1].change.emit()
                            first.change.emit();
                            second.change.emit();

                            window.fIdx = fIdx;
                            window.pfIdx = pfIdx;
                        }
                        """)
p2.add_tools(HoverTool(tooltips=None, callback=hoverCallback, mode='mouse'))
sliderCallback = CustomJS(
    args={
        'acquistionTimes': acquistionTimes,
        'images': CDSimages,
        'CRB': CRB},
    code="""
    window.taIdx = Math.floor((cb_obj.value - cb_obj.start ) / cb_obj.step)
    console.log(window.taIdx)
    images[0].data.imageData = [CRB.map(PF => PF.map(f => f[window.taIdx][0])).flat()]
    images[1].data.imageData = [CRB.map(PF => PF.map(f => f[window.taIdx][1])).flat()]
    images[0].change.emit();
    images[1].change.emit();
    """
    )
slider.js_on_change('value', sliderCallback)


# put the results in a column and show
show(column(p2, pGrad, slider))