"""Advanced skin texture and feature analysis."""
from typing import Dict, Tuple, List
import numpy as np
import cv2
from skimage.feature import local_binary_pattern, graycomatrix, graycoprops
from skimage import exposure

class SkinTextureAnalyzer:
    def __init__(self):
        self.lbp_radius = 3
        self.lbp_n_points = 8 * self.lbp_radius
        
    def analyze_texture(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
        """Analyze skin texture using multiple techniques."""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l_enhanced = clahe.apply(l_channel)
        
        # Calculate Local Binary Patterns
        lbp = local_binary_pattern(l_enhanced, self.lbp_n_points, self.lbp_radius, method='uniform')
        lbp_masked = cv2.bitwise_and(lbp.astype(np.uint8), mask)
        
        # Calculate GLCM features
        glcm = graycomatrix(l_enhanced, [1], [0], 256, symmetric=True, normed=True)
        contrast = graycoprops(glcm, 'contrast')[0, 0]
        correlation = graycoprops(glcm, 'correlation')[0, 0]
        energy = graycoprops(glcm, 'energy')[0, 0]
        homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
        
        # Color variation analysis in a/b channels
        a_stats = self._analyze_channel_variation(a_channel, mask)
        b_stats = self._analyze_channel_variation(b_channel, mask)
        
        return {
            'texture_contrast': float(contrast),
            'texture_correlation': float(correlation),
            'texture_energy': float(energy),
            'texture_homogeneity': float(homogeneity),
            'redness_variation': float(a_stats['std']),
            'yellowness_variation': float(b_stats['std']),
            'texture_uniformity': float(self._calculate_uniformity(lbp_masked))
        }
    
    def detect_skin_features(
        self, image: np.ndarray, mask: np.ndarray
    ) -> Tuple[np.ndarray, List[Dict[str, float]]]:
        """Detect and classify different skin features."""
        # Convert to LAB and enhance
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Enhance local contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l_enhanced = clahe.apply(l)
        
        # Calculate local standard deviation (texture variation)
        local_std = self._local_standard_deviation(l_enhanced, 5)
        
        # Multi-scale feature detection
        feature_mask = np.zeros_like(mask)
        features = []
        
        # Detect features at different scales
        for scale in [0.5, 1.0, 2.0]:
            scaled_img = cv2.resize(l_enhanced, None, fx=scale, fy=scale)
            scaled_mask = cv2.resize(mask, None, fx=scale, fy=scale)
            
            # Apply bilateral filter for edge-preserving smoothing
            smoothed = cv2.bilateralFilter(scaled_img, 9, 75, 75)
            
            # Detect local maxima and minima
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
            local_max = cv2.dilate(smoothed, kernel) == smoothed
            local_min = cv2.erode(smoothed, kernel) == smoothed
            
            # Combine detections and scale back
            detection = cv2.resize((local_max | local_min).astype(np.uint8), 
                                 (mask.shape[1], mask.shape[0]))
            
            feature_mask |= detection & mask
        
        # Analyze detected features
        contours, _ = cv2.findContours(feature_mask, cv2.RETR_EXTERNAL, 
                                     cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 20 <= area <= 1000:  # Filter by size
                x, y, w, h = cv2.boundingRect(contour)
                roi = image[y:y+h, x:x+w]
                mask_roi = mask[y:y+h, x:x+w]
                
                if roi.size > 0 and mask_roi.size > 0:
                    feature_stats = self._analyze_feature(roi, mask_roi)
                    feature_stats.update({
                        'x': x, 'y': y,
                        'width': w, 'height': h,
                        'area': area
                    })
                    features.append(feature_stats)
        
        return feature_mask, features
    
    def _analyze_channel_variation(self, channel: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
        """Analyze statistical properties of a color channel in masked region."""
        masked_channel = cv2.bitwise_and(channel, mask)
        pixels = masked_channel[mask > 0]
        
        return {
            'mean': float(np.mean(pixels)),
            'std': float(np.std(pixels)),
            'min': float(np.min(pixels)),
            'max': float(np.max(pixels))
        }
    
    def _calculate_uniformity(self, lbp_image: np.ndarray) -> float:
        """Calculate texture uniformity from LBP image."""
        hist, _ = np.histogram(lbp_image, bins=np.arange(0, 50), density=True)
        return float(np.sum(hist ** 2))
    
    def _local_standard_deviation(self, image: np.ndarray, window_size: int) -> np.ndarray:
        """Calculate local standard deviation using a sliding window."""
        kernel = np.ones((window_size, window_size)) / (window_size ** 2)
        mean = cv2.filter2D(image.astype(float), -1, kernel)
        mean_sq = cv2.filter2D(image.astype(float)**2, -1, kernel)
        return np.sqrt(mean_sq - mean**2)
    
    def _analyze_feature(self, roi: np.ndarray, mask_roi: np.ndarray) -> Dict[str, float]:
        """Analyze an individual detected feature."""
        # Convert to LAB
        lab_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab_roi)
        
        # Calculate statistics for each channel
        l_stats = self._analyze_channel_variation(l, mask_roi)
        a_stats = self._analyze_channel_variation(a, mask_roi)
        b_stats = self._analyze_channel_variation(b, mask_roi)
        
        return {
            'brightness': l_stats['mean'],
            'redness': a_stats['mean'],
            'yellowness': b_stats['mean'],
            'contrast': l_stats['std']
        }
