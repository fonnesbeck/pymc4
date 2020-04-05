"""
Covariance Functions for PyMC4's Gaussian Process module.

"""

from abc import abstractmethod
import tensorflow_probability as tfp

__all__ = [
    #     "Constant",
    #     "WhiteNoise",
    "ExpQuad",
    #     "RatQuad",
    #     "Exponential",
    #     "Matern52",
    #     "Matern32",
    #     "Linear",
    #     "Polynomial",
    #     "Cosine",
    #     "Periodic",
    #     "WarpedInput",
    #     "Gibbs",
    #     "Coregion",
    #     "ScaledCov",
    #     "Kron",
]


class Covariance:
    r"""Base class of all Covariance functions for Gaussian Process"""

    def __init__(self, feature_ndims=1, **kwargs):
        # TODO: Implement the `diag` parameter as in PyMC3.
        self._feature_ndims = feature_ndims
        self._kernel = self._init_kernel(feature_ndims=self.feature_ndims, **kwargs)
        if self._kernel is not None:
            # wrap the kernel in FeatureScaled kernel for ARD
            self._scale_diag = kwargs.pop("scale_diag", 1.0)
            self._kernel = tfp.math.psd_kernels.FeatureScaled(
                self._kernel, scale_diag=self._scale_diag
            )

    @abstractmethod
    def _init_kernel(self, feature_ndims, **kwargs):
        raise NotImplementedError("Your Covariance class should override this method")

    def __call__(self, X1, X2, **kwargs):
        return self._kernel.matrix(X1, X2, **kwargs)

    def evaluate_kernel(self, X1, X2, **kwargs):
        """Evaluate kernel at certain points

        Parameters
        ----------
        X1 : tensor, array-like
            First point(s)
        X2 : tensor, array-like
            Second point(s)
        """
        return self._kernel.apply(X1, X2, **kwargs)

    def __add__(self, cov2):
        return CovarianceAdd(self, cov2)

    def __mul__(self, cov2):
        return CovarianceProd(self, cov2)

    def __radd__(self, other):
        return CovarianceAdd(self, other)

    def __rmul__(self, other):
        return CovarianceProd(self, other)

    @property
    def feature_ndims(self):
        return self._feature_ndims


class Combination(Covariance):
    r"""Combination of two or more covariance functions

    Parameters
    ----------
    cov1 : pm.gp.Covariance
        First covariance function.
    cov2 : pm.gp.Covariance
        Second covariance function.
    """

    def __init__(self, cov1, cov2):
        self.cov1 = cov1
        self.cov2 = cov2
        if isinstance(cov1, Covariance) and isinstance(cov2, Covariance):
            if cov1.feature_ndims != cov2.feature_ndims:
                raise ValueError("Cannot combine kernels with different feature_ndims")

    @property
    def feature_ndims(self):
        if isinstance(self.cov1, Covariance):
            return self.cov1.feature_ndims
        else:
            return self.cov2.feature_ndims


class CovarianceAdd(Combination):
    r"""Addition of two or more covariance functions.

    Parameters
    ----------
    feature_ndims : int
        number of rightmost dims to include in kernel computation
    """

    def __call__(self, X1, X2, **kwargs):
        if not isinstance(self.cov1, Covariance):
            return self.cov1 + self.cov2(X1, X2, **kwargs)
        elif not isinstance(self.cov2, Covariance):
            return self.cov2 + self.cov1(X1, X2, **kwargs)
        else:
            return self.cov1(X1, X2, **kwargs) + self.cov2(X1, X2, **kwargs)


class CovarianceProd(Combination):
    r"""Product of two or more covariance functions.

    Parameters
    ----------
    feature_ndims : int
        number of rightmost dims to include in kernel computation
    """

    def __call__(self, X1, X2, **kwargs):
        if not isinstance(self.cov1, Covariance):
            return self.cov1 * self.cov2(X1, X2, **kwargs)
        elif not isinstance(self.cov2, Covariance):
            return self.cov2 * self.cov1(X1, X2, **kwargs)
        else:
            return self.cov1(X1, X2, **kwargs) * self.cov2(X1, X2, **kwargs)


class Stationary(Covariance):
    r"""Base class for all Stationary Covariance functions"""

    @property
    def length_scale(self):
        r"""Length scale of the covariance function"""
        return self._length_scale


class ExpQuad(Stationary):
    r"""Exponentiated Quadratic Stationary Covariance Function.
    Commonly known as the Radial Basis Kernel Function.

    .. math::
       k(x, x') = \sigma^2 \mathrm{exp}\left[ -\frac{(x - x')^2}{2 l^2} \right]

    where :math:`\sigma` = ``amplitude``
          :math:`l` = ``length_scale``

    Parameters
    ----------
    amplitude : tensor, array-like
        The :math:`\sigma` parameter of RBF kernel, amplitude > 0
    length_scale : tensor, array-like
        The :math:`l` parameter of the RBF kernel
    feature_ndims : int, optional
        number of rightmost dims to include in kernel computation
    kwargs : optional
        Other keyword arguments that tfp's ``ExponentiatedQuadratic`` kernel takes
    """

    def __init__(self, length_scale, amplitude=1.0, feature_ndims=1, **kwargs):
        self._amplitude = amplitude
        self._length_scale = length_scale
        super().__init__(feature_ndims=feature_ndims, **kwargs)

    def _init_kernel(self, feature_ndims, **kwargs):
        return tfp.math.psd_kernels.ExponentiatedQuadratic(
            length_scale=self._length_scale, amplitude=self._amplitude, feature_ndims=feature_ndims
        )

    @property
    def amplitude(self):
        r"""Amplitude of the kernel function"""
        return self._amplitude
