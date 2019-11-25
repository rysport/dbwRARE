import numpy as np
from supportFunctions import weightsFromFraction, getDephasingTimes, weightedCrbTwoEchoes
import bokeh
from bokeh.plotting import figure, output_file, output_notebook, show
from bokeh.models import ColumnDataSource, CustomJS, Title, HoverTool, Span, NormalHead, Arrow
from bokeh.palettes import viridis
from bokeh.layouts import column, row
from bokeh.models.widgets import Slider

numFrac = 256
numPF = 256
W = weightsFromFraction(np.linspace(0,1,numFrac))

#output_file()

p1 = figure(height=200, width=200, toolbar_location=None, title='Weights')

l = p1.line(np.linspace(0,1,numFrac), W[1], legend_label="w1", color='navy')
l = p1.line(np.linspace(0,1,numFrac), W[1], legend_label="w2", color='chocolate')

B0 = 3 # Tesla

acquistionTimes = np.arange(start=2.3, stop=6.6, step=.5)
numTa = len(acquistionTimes)
partialFourierFactors = np.linspace(start=0.5, stop=1, num=numPF)
dephasingTimes = np.empty(shape=(numPF,numFrac,numTa,2), dtype=np.float32)
firstEchoFractions = np.linspace(start=0, stop=1, num=numFrac)
NSA = np.empty(shape=(numPF,numFrac,numTa,2), dtype=np.float32) # [W, F] at 0% fat fraction

for nt, ta in enumerate(acquistionTimes):
    for nPF,PF in enumerate(partialFourierFactors):
        for nf, f in enumerate(firstEchoFractions):
            dephasingTimes[nPF, nf, nt, :] = getDephasingTimes(ta/1.0e3, PF, f)
            weights = weightsFromFraction(f)
            NSA[nPF, nf, nt, :] = np.reciprocal( weightedCrbTwoEchoes(B0, dephasingTimes[nPF, nf, nt, :], weights) )
    print(100.*(nt+1)/numTa)

pWat = figure(height=350, width=350, toolbar_location=None, title='Water NSA (3T)')
pFat = figure(height=350, width=350, toolbar_location=None, title='Fat NSA (3T)')
CDSimages = [ColumnDataSource({'imageData': [NSA[:,:,-1,0]]}),
             ColumnDataSource({'imageData': [NSA[:,:,-1,1]]})]
pWat.image(image='imageData', x=0, y=0, dw=numFrac, dh=numPF, palette=viridis(100), source=CDSimages[0])
pFat.image(image='imageData', x=0, y=0, dw=numFrac, dh=numPF, palette=viridis(100), source=CDSimages[1])

for p in [pWat, pFat]:
    p.xaxis.ticker = [0, (numFrac-1)/4, (numFrac-1)/2, 3*(numFrac-1)/4, numFrac-1]
    p.xaxis.major_label_overrides = {0:'0',
                                     (numFrac-1)/4: '.25',
                                     (numFrac-1)/2: '.5',
                                     3*(numFrac-1)/4: '.75',
                                     numFrac-1: '1'}
    p.yaxis.ticker = [0, (numPF-1)/2, numPF-1]
    p.yaxis.major_label_overrides = {0:'0.5',
                                     (numPF-1)/2: '.75',
                                     numPF-1: '1.0'}

pWat.x_range.range_padding = pWat.y_range.range_padding = 0
pFat.x_range.range_padding = pFat.y_range.range_padding = 0
spans = [Span(location=-1, dimension='height', line_color='navy', line_dash='dashed'),
         Span(location=-1, dimension='height', line_color='chocolate', line_dash='dashed')]
pGrad = figure(height=350, width=350, toolbar_location=None, title='Gradients')
pGrad.add_layout(spans[0])
pGrad.add_layout(spans[1])
CDSFirst = ColumnDataSource({'t': [0, 0, .5, .5], 'amp': [0, 1, 1, 0]})
CDSSecond = ColumnDataSource({'t': [.5, .5, 1, 1], 'amp': [0, -1, -1, 0]})
pGrad.line(x='t', y='amp', color='navy', line_width=2, source=CDSFirst)
pGrad.line(x='t', y='amp', color='chocolate', line_width=2, source=CDSSecond)

pCompass = figure(height=350, width=350, toolbar_location=None, title='Fat vectors', x_range=(-1.1, 1.1), y_range=(-1.1, 1.1))
pCompass.circle(0, 0, radius=1, fill_color=None, line_color='black')
CDSArrow = [ColumnDataSource({'x': [0, 0], 'y': [0, 0]}),
            ColumnDataSource({'x': [0, 0], 'y': [0, 0]})]
pCompass.line(x='x', y='y', color='navy', line_width=2, source=CDSArrow[0])
pCompass.line(x='x', y='y', color='chocolate', line_width=2, source=CDSArrow[1])

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
                         'arrows': CDSArrow,
                         'first': CDSFirst,
                         'slider': slider,
                         'second': CDSSecond,},
                        code="""
                        if ( isFinite(cb_data['geometry']['x']) && isFinite(cb_data['geometry']['y']) ) {
                            let ta = slider.value / 1000.0
                            if (typeof window.taIdx == 'undefined') {
                                window.taIdx = dephasingTimes[0][0].length - 1;
                            }
                            let fIdx = Math.floor(cb_data["geometry"]['x']) % firstEchoFractions.length;
                            let pfIdx = Math.floor(cb_data["geometry"]['y']);
                            first.data.t[2] = first.data.t[3] = ta*firstEchoFractions[fIdx];
                            second.data.t[0] = second.data.t[1] = ta*firstEchoFractions[fIdx];
                            second.data.t[2] = second.data.t[3] = ta;
                            first.data.amp[1] = first.data.amp[2] = partialFourierFactors[pfIdx] / firstEchoFractions[fIdx];
                            second.data.amp[1] = second.data.amp[2] = - partialFourierFactors[pfIdx] / (1 - firstEchoFractions[fIdx]);
                            spans[0].location = ta/2.0 + dephasingTimes[pfIdx][fIdx][window.taIdx][0];
                            spans[1].location = ta/2.0 + dephasingTimes[pfIdx][fIdx][window.taIdx][1];
                            
                            spans[0].change.emit();
                            spans[1].change.emit();
                            first.change.emit();
                            second.change.emit();
                            let omega = 2*Math.PI*42.58*3*3.4
                            
                            for (let i = 0; i < 2; i++) {
                                arrows[i].data.x[1] = Math.cos(omega*dephasingTimes[pfIdx][fIdx][window.taIdx][i]);
                                arrows[i].data.y[1] = Math.sin(omega*dephasingTimes[pfIdx][fIdx][window.taIdx][i]);
                                arrows[i].change.emit();
                            }
                            
                            window.fIdx = fIdx;
                            window.pfIdx = pfIdx;
                        }
                        """)
pWat.add_tools(HoverTool(tooltips=None, callback=hoverCallback, mode='mouse'))
pFat.add_tools(HoverTool(tooltips=None, callback=hoverCallback, mode='mouse'))
sliderCallback = CustomJS(
    args={
        'acquistionTimes': acquistionTimes,
        'images': CDSimages,
        'NSA': NSA},
    code="""
    window.taIdx = Math.floor((cb_obj.value - cb_obj.start ) / cb_obj.step)
    console.log(window.taIdx)
    images[0].data.imageData = [NSA.map(PF => PF.map(f => f[window.taIdx][0])).flat()]
    images[1].data.imageData = [NSA.map(PF => PF.map(f => f[window.taIdx][1])).flat()]
    images[0].change.emit();
    images[1].change.emit();
    """
    )
slider.js_on_change('value', sliderCallback)


# put the results in a column and show
show(column(row(pWat, pFat), row(pGrad, pCompass), slider))
