import numpy as np
def weightsFromFraction(f):
    
    w1 = np.sqrt(  f**2    / ((1-f)**2 + f**2) );
    w2 = np.sqrt( (1-f)**2 / ((1-f)**2 + f**2) );
    return (w1, w2)

# ta - Available acquisition time
# PF - Partial Fourier Fraction
# f - First readout duration / ta
def getDephasingTimes(ta, PF, f):
    firstDur = ta * f
    secondDur = ta * (1-f)
    spinecho = ta/2
    # Time-to-center
    ttc = [firstDur / (2*PF),
           secondDur * (1 - 1/(2 * PF))]
    return [ttc[0] - spinecho, firstDur + ttc[1] - spinecho]

# B0 - Field strength
# t - Dephasing times [2, 1]
# w - Weights [2, 1]
def weightedCrbTwoEchoes(B0, t, w):
    # Fat off-resonance at 3.4ppm
    omega = 2*np.pi*42.58*B0*3.4;

    c1 = np.cos(omega * t[0]);
    c2 = np.cos(omega * t[1]);

    # Numerator (common)
    N = (w[0]*w[1]*(c1 - c2)) ** 2
    # CRB [Water, Fat]
    CRB = [N / ((w[0]*c1)**2 + (w[1]*c2)**2),
           N / (w[0]**2 + w[1]**2)]
    return CRB