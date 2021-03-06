# -*- coding: utf-8 -*-
"""
The :mod:`parsimony.functions.taylor` module contains classes for Taylor
approximations of functions. These represent the original mathematical
but where the function, gradient, Hessian etc. have been replaces by the
corresponding ones of the Taylor approximation.

Loss functions should be stateless. Loss functions may be shared and copied
and should therefore not hold anything that cannot be recomputed the next time
it is called.

Created on Tue Sep 20 11:17:14 2016

Copyright (c) 2013-2014, CEA/DSV/I2BM/Neurospin. All rights reserved.

@author:  Tommy Löfstedt
@email:   lofstedt.tommy@gmail.com
@license: BSD 3-clause.
"""
import abc
import copy
import types
from six import with_metaclass

import numpy as np

try:
    from . import properties  # Only works when imported as a package.
except ValueError:
    import parsimony.functions.properties as properties  # Run as a script.
try:
    from . import combinedfunctions  # Only works when imported as a package.
except ValueError:
    import parsimony.functions.combinedfunctions as combinedfunctions  # Run as a script.
try:
    from .multiblock import losses as multiblocklosses  # Only works when imported as a package.
except ValueError:
    import parsimony.functions.multiblock.losses as multiblocklosses  # Run as a script.
try:
    from .multiblock import properties as multiblockprops  # Only works when imported as a package.
except ValueError:
    import parsimony.functions.multiblock.properties as multiblockprops  # Run as a script.
import parsimony.utils as utils
import parsimony.utils.consts as consts


__all__ = ["BaseTaylor", "FirstOrderTaylorApproximation",
           "MultiblockFirstOrderTaylorApproximation",
           "FirstOrderTaylorWrapper"]


class BaseTaylor(with_metaclass(abc.ABCMeta, properties.Function)):
    """This is the base class for all Taylor approximation functions.
    """
    def __init__(self, function, point):

        self.function = function
        self.at_point(point)

    def reset(self):
        """Free any cached computations from previous use of this Function.

        From the interface "CompositeFunction".
        """
        if self.function is not None:
            self.function.reset()

        self.f_at_point = None

    def at_point(self, point):
        """Redefine the point around which the Taylor approximation is
        computed.

        Parameters
        ----------
        point : numpy array
            The point around which the Taylor approximation is computed.
        """
        self.point = point

        self.reset()

    def _precompute(self):
        """Precopmute whatever can be precomputed, e.g. the function value at
        point a.

        From the interface "BaseTaylor".
        """
        if self.f_at_point is None:
            self.f_at_point = self.function.f(self.point)


class MultiblockBaseTaylor(with_metaclass(abc.ABCMeta,
                                          multiblockprops.MultiblockFunction)):
    """This is the base class for all Taylor approximation functions of the
    multiblock flavour.
    """
    def __init__(self, function, point, indices):

        self.function = function
        self.at_point(point)
        self.indices = list(indices)
        for i in range(len(indices)):
            indices[i] = int(indices[i])

    def reset(self):
        """Free any cached computations from previous use of this Function.

        From the interface "CompositeFunction".
        """
        if self.function is not None:
            self.function.reset()

        self.f_at_point = None

    def at_point(self, point):
        """Redefine the point around which the Taylor approximation is
        computed.

        Parameters
        ----------
        point : numpy array
            The point around which the Taylor approximation is computed.
        """
        self.point = point

        self.reset()

    def _precompute(self):
        """Precopmute whatever can be precomputed, e.g. the function value at
        point a.

        From the interface "BaseTaylor".
        """
        if self.f_at_point is None:
            self.f_at_point = self.function.f([self.point[self.indices[0]],
                                               self.point[self.indices[1]]])


class FirstOrderTaylorWrapper(properties.MajoriserFunction):

    def __init__(self):
        pass

    def __call__(self, function, point):

        fun = copy.deepcopy(function)

        if isinstance(fun, combinedfunctions.CombinedFunction):
            # TODO: Not very good OO here ...
            # TODO: Beware of API changes here!
            for i in len(fun._f):
                f = fun._f[i]
                if isinstance(f, BaseTaylor):
                    fun._f[i] = self._wrap(f, point)
            for i in len(fun._d):
                d = fun._d[i]
                if isinstance(d, BaseTaylor):
                    fun._d[i] = self._wrap(d, point)
            for i in len(fun._N):
                N = fun._N[i]
                if isinstance(N, BaseTaylor):
                    fun._N[i] = self._wrap(N, point)

            def new_at_point(self, x):
                for f in fun._f:
                    if isinstance(f, BaseTaylor):
                        f.at_point(x)
                for d in fun._d:
                    if isinstance(d, BaseTaylor):
                        d.at_point(x)
                for N in fun._N:
                    if isinstance(N, BaseTaylor):
                        N.at_point(x)

            fun.at_point = types.MethodType(new_at_point, fun)

        elif isinstance(fun, multiblocklosses.CombinedMultiblockFunction):
            # TODO: Not very good OO here ...
            # TODO: Beware of API changes here!
            for i in range(len(fun._f)):
                fi = fun._f[i]
                for j in range(len(fi)):
                    fij = fun._f[i][j]
                    for k in range(len(fij)):
                        fijk = fun._f[i][j][k]
                        if isinstance(fijk, BaseTaylor):
                            fun._f[i][j][k] = self._mb_wrap(fijk, point)
            for i in range(len(fun._d)):
                di = fun._d[i]
                for k in range(len(di)):
                    dik = fun._d[i][k]
                    if isinstance(dik, BaseTaylor):
                        fun._d[i][k] = self._mb_wrap(dik, point)

            for i in range(len(fun._N)):
                Ni = fun._N[i]
                for k in range(len(Ni)):
                    Nik = fun._N[i][k]
                    if isinstance(Nik, BaseTaylor):
                        fun._N[i][k] = self._mb_wrap(Nik, point)

            def new_at_point(self, x):
                for fi in fun._f:
                    for fij in fi:
                        for fijk in fij:
                            if isinstance(fijk, BaseTaylor):
                                fijk.at_point(x)
                for di in fun._d:
                    for dij in di:
                        if isinstance(dij, BaseTaylor):
                            dij.at_point(x)
                for Ni in fun._N:
                    for Nij in Ni:
                        if isinstance(Nij, BaseTaylor):
                            Nij.at_point(x)

            fun.at_point = types.MethodType(new_at_point, fun)

        elif isinstance(fun, multiblockprops.MultiblockFunction):
            fun = self._mb_wrap(fun, point)

        else:
            fun = self._wrap(fun, point)

        return fun

    def _wrap(self, fun, point):
        if hasattr(fun, "_taylor_point"):
            raise RuntimeError("The function appears to already be a Taylor "
                               "approximation!")
        else:
            fun._taylor_point = point
        if hasattr(fun, "_taylor_f_at_point"):
            raise RuntimeError("The function appears to already be a Taylor "
                               "approximation!")
        else:
            if isinstance(fun, combinedfunctions.CombinedFunction):
                fun._taylor_f_at_point = fun._f(point)
            else:
                fun._taylor_f_at_point = fun.f(point)
        if hasattr(fun, "_taylor_grad_f_at_point"):
            raise RuntimeError("The function appears to already be a Taylor "
                               "approximation!")
        else:
            if isinstance(fun, combinedfunctions.CombinedFunction):
                fun._taylor_grad_f_at_point = fun._grad_f(point)
            else:
                fun._taylor_grad_f_at_point = fun.grad(point)

        # Redefine the function value
        def new_f(self, x):
            val = self._taylor_f_at_point \
                + np.dot(self._taylor_grad_f_at_point.T,
                         x - self._taylor_point)

            # Add function values from the penalties:
            if isinstance(fun, combinedfunctions.CombinedFunction):
                val += self._non_f(x)

            return val[0, 0]

        fun.f = types.MethodType(new_f, fun)

        # Redefine the gradient
        def new_grad(self, x):
            grad = self._taylor_grad_f_at_point

            # Add gradients from the penalties:
            if isinstance(fun, combinedfunctions.CombinedFunction):
                grad = grad + self._grad_non_f(x)

            return grad

        fun.grad = types.MethodType(new_grad, fun)

#        # Redefine the Lipschitz constant, if it is used
#        if hasattr(fun, 'L'):
#            def new_L(self, x=None):
#                return consts.FLOAT_EPSILON
#            fun.L = types.MethodType(new_L, fun)

        return fun

    def _mb_wrap(self, fun, point):
        if hasattr(fun, "_taylor_point"):
            raise RuntimeError("The function appears to already be a Taylor "
                               "approximation!")
        else:
            fun._taylor_point = point
        if hasattr(fun, "_taylor_f_at_point"):
            raise RuntimeError("The function appears to already be a Taylor "
                               "approximation!")
        else:
            fun._taylor_f_at_point = fun._f(point)
        if hasattr(fun, "_taylor_grad_f_at_point"):
            raise RuntimeError("The function appears to already be a Taylor "
                               "approximation!")
        else:
            fun._taylor_grad_f_at_point = [0] * len(point)
            for i in range(len(point)):
                fun._taylor_grad_f_at_point[i] = fun._grad_f(point, i)
#        if hasattr(fun, "_taylor_old_f"):
#            raise RuntimeError("The function appears to already be a Taylor "
#                               "approximation!")
#        else:
#            fun._taylor_old_f = fun.f
#        if hasattr(fun, "_taylor_old_grad"):
#            raise RuntimeError("The function appears to already be a Taylor "
#                               "approximation!")
#        else:
#            fun._taylor_old_grad = fun.grad

        # Redefine the function value
        def new_f(self, x):
            val = 0.0
            for i in range(len(self._taylor_point)):
                val += self._taylor_f_at_point \
                    + np.dot(self._taylor_grad_f_at_point[i].T,
                             x - self._taylor_point[i])

            # Add function values from the penalties:
            val += self._non_f(x)

            return val[0, 0]

        fun.f = types.MethodType(new_f, fun)

        # Redefine the gradient
        def new_grad(self, x, index):
            grad = self._taylor_grad_f_at_point

            # Add gradients from the penalties:
            grad = grad + self._grad_non_f(x, index)

            return grad

        fun.grad = types.MethodType(new_grad, fun)

#        # Redefine the Lipschitz constant, if it is used
#        if hasattr(fun, 'L'):
#            def new_L(self, x=None):
#                return consts.FLOAT_EPSILON
#            fun.L = types.MethodType(new_L, fun)

        return fun


class FirstOrderTaylorApproximation(BaseTaylor,
                                    properties.Gradient,
                                    properties.LipschitzContinuousGradient):
    """A first order Taylor approximation of a function around a point, a, i.e.

        T(x) = f(a) + <grad(f(a)) | x - a>.
    """
    def __init__(self, function, point):

        super(FirstOrderTaylorApproximation, self).__init__(function, point)

        self.reset()

    def reset(self):
        """Free any cached computations from previous use of this Function.

        From the interface "CompositeFunction".
        """
        super(FirstOrderTaylorApproximation, self).reset()

        self.grad_at_point = None

    def _precompute(self):
        """Precopmute whatever can be precomputed, e.g. the function value at
        point a.

        From the interface "BaseTaylor".
        """
        super(FirstOrderTaylorApproximation, self)._precompute()

        if self.grad_at_point is None:
            self.grad_at_point = self.function.grad(self.point)

    def f(self, w):
        """Function value.

        From the interface "CompositeFunction".
        """
        self._precompute()

        f = self.f_at_point + np.dot(self.grad_at_point, w - self.point)

        return f

    def grad(self, w):
        """Gradient of the function.

        From the interface "Gradient".

        Parameters
        ----------
        w : numpy array (p-by-1)
            The point at which to evaluate the gradient.
        """
        self._precompute()

        grad = self.grad_at_point

        return grad

    def L(self, w=None):
        """Lipschitz constant of the gradient.

        From the interface "LipschitzContinuousGradient".

        Parameters
        ----------
        w : numpy array (p-by-1), optional
            The point at which to evaluate the Lipschitz constant.
        """
        # Any positive real number suffices, but a small one will give a larger
        # step in e.g. proximal gradient descent.
        return np.sqrt(consts.TOLERANCE)


class MultiblockFirstOrderTaylorApproximation(MultiblockBaseTaylor,
                                              multiblockprops.MultiblockGradient,
                                              multiblockprops.MultiblockLipschitzContinuousGradient):
    """A first order Taylor approximation of a function around a point, a, i.e.

        T(x) = f(a) + <grad(f(a)) | x - a>.
    """
    def __init__(self, function, point, indices):

        super(MultiblockFirstOrderTaylorApproximation, self).__init__(function,
                                                                      point,
                                                                      indices)

        self.reset()

    def reset(self):
        """Free any cached computations from previous use of this Function.

        From the interface "CompositeFunction".
        """
        super(MultiblockFirstOrderTaylorApproximation, self).reset()

        self.grad_at_point = None

    def _precompute(self):
        """Precopmute whatever can be precomputed, e.g. the function value at
        a point.

        From the interface "BaseTaylor".
        """
        super(MultiblockFirstOrderTaylorApproximation, self)._precompute()

        if self.grad_at_point is None:
            self.grad_at_point = [0] * len(self.indices)
            for i in range(len(self.indices)):
                self.grad_at_point[i] = self.function.grad([self.point[self.indices[0]],
                                                            self.point[self.indices[1]]],
                                                           i)

    def f(self, w):
        """Function value.

        From the interface "CompositeFunction".

        Parameters
        ----------
        w : numpy array (p-by-1)
            The point at which to evaluate the function.
        """
        self._precompute()

        f = self.f_at_point
        for i in range(len(self.indices)):
            f = f + np.dot(self.grad_at_point[i].T,
                           w[i] - self.point[self.indices[i]])[0, 0]

        return f

    def grad(self, w, index):
        """Gradient of the function.

        From the interface "Gradient".

        Parameters
        ----------
        w : numpy array (p-by-1)
            The point at which to evaluate the gradient.
        """
        self._precompute()

        grad = self.grad_at_point[index]

        return grad

    def L(self, w, index):
        """Lipschitz constant of the gradient.

        From the interface "LipschitzContinuousGradient".

        Parameters
        ----------
        x : numpy array (p-by-1), optional
            The point at which to evaluate the Lipschitz constant.
        """
        # Any positive real number suffices, but a small one will give a larger
        # step in e.g. proximal gradient descent.
        return np.sqrt(consts.TOLERANCE)
