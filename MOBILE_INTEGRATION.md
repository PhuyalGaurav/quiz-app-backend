# Mobile App Integration Guide

This document provides guidance on integrating this Django backend with a React Native mobile app.

## Initial Setup

1. **Install Required Packages**

```bash
# In your React Native app directory
npm install axios @react-navigation/native @react-native-async-storage/async-storage jwt-decode
```

2. **Set Up API Client**

Create an API client that will handle communication with the backend:

```javascript
// src/services/api.js
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Set your API base URL
const API_URL = 'https://your-backend-url.com/api/';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to attach JWT token to requests
apiClient.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('access_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If the error is due to an expired token (401) and we haven't already tried to refresh
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = await AsyncStorage.getItem('refresh_token');
        
        if (!refreshToken) {
          // No refresh token available, redirect to login
          return Promise.reject(error);
        }
        
        // Attempt to refresh the token
        const response = await axios.post(`${API_URL}token/refresh/`, {
          refresh: refreshToken
        });
        
        // Store new tokens
        const { access } = response.data;
        await AsyncStorage.setItem('access_token', access);
        
        // Update the original request with new token
        originalRequest.headers['Authorization'] = `Bearer ${access}`;
        
        // Retry the original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        // If refresh token is invalid, redirect to login
        await AsyncStorage.removeItem('access_token');
        await AsyncStorage.removeItem('refresh_token');
        // You would handle redirection to login here
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

## Authentication

### User Registration

```javascript
// src/services/authService.js
import apiClient from './api';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const register = async (userData) => {
  try {
    const response = await apiClient.post('register/', userData);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const login = async (credentials) => {
  try {
    const response = await apiClient.post('token/', credentials);
    
    const { access, refresh } = response.data;
    
    // Store tokens
    await AsyncStorage.setItem('access_token', access);
    await AsyncStorage.setItem('refresh_token', refresh);
    
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const logout = async () => {
  await AsyncStorage.removeItem('access_token');
  await AsyncStorage.removeItem('refresh_token');
  // You would handle any other cleanup here
};

export const getUserProfile = async () => {
  try {
    const response = await apiClient.get('profile/');
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};
```

## Quiz Services

```javascript
// src/services/quizService.js
import apiClient from './api';
import * as ImagePicker from 'expo-image-picker';

export const getQuizzes = async () => {
  try {
    const response = await apiClient.get('quizzes/');
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const getQuizById = async (id) => {
  try {
    const response = await apiClient.get(`quizzes/${id}/`);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const getQuizByShareCode = async (shareCode) => {
  try {
    const response = await apiClient.get(`join/${shareCode}/`);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const uploadImage = async () => {
  try {
    // Request permission to access camera roll
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      throw new Error('Permission to access media library was denied');
    }
    
    // Let user pick an image
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 1,
    });
    
    if (result.canceled) {
      throw new Error('Image picking was cancelled');
    }
    
    // Create form data for upload
    const formData = new FormData();
    formData.append('image', {
      uri: result.assets[0].uri,
      name: 'photo.jpg',
      type: 'image/jpeg',
    });
    
    // Upload the image
    const response = await apiClient.post('upload-image/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const createQuizFromImage = async (imageId, quizData) => {
  try {
    const data = {
      image_id: imageId,
      title: quizData.title,
      duration_minutes: quizData.durationMinutes || 10,
      is_public: quizData.isPublic || false,
    };
    
    const response = await apiClient.post('create-quiz-from-image/', data);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const startQuizSession = async (quizId) => {
  try {
    const response = await apiClient.post('sessions/', { quiz: quizId });
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const submitAnswer = async (sessionId, questionId, choiceId) => {
  try {
    const response = await apiClient.post(`sessions/${sessionId}/submit-answer/`, {
      question_id: questionId,
      choice_id: choiceId,
    });
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const completeQuizSession = async (sessionId) => {
  try {
    const response = await apiClient.post(`sessions/${sessionId}/complete/`);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const shareQuiz = async (quizId, recipientEmailOrUsername, permissionType = 'attempt') => {
  try {
    const data = {
      shared_with: recipientEmailOrUsername,
      permission_type: permissionType,
    };
    
    const response = await apiClient.post(`quizzes/${quizId}/share/`, data);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};

export const getQuizQrCode = async (quizId) => {
  try {
    const response = await apiClient.get(`quizzes/${quizId}/qr_code/`);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
};
```

## Example Screens

### Login Screen

```jsx
import React, { useState } from 'react';
import { View, TextInput, Button, StyleSheet, Text, Alert } from 'react-native';
import { login } from '../services/authService';

const LoginScreen = ({ navigation }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!username || !password) {
      Alert.alert('Error', 'Please enter both username and password');
      return;
    }

    try {
      setLoading(true);
      await login({ username, password });
      navigation.navigate('Home');
    } catch (error) {
      Alert.alert('Login Failed', error.message || 'Please check your credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Quiz App</Text>
      <TextInput
        style={styles.input}
        placeholder="Username"
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      <Button title={loading ? "Logging in..." : "Login"} onPress={handleLogin} disabled={loading} />
      <Text style={styles.registerLink} onPress={() => navigation.navigate('Register')}>
        Don't have an account? Register here
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 5,
    marginBottom: 15,
    paddingHorizontal: 10,
  },
  registerLink: {
    marginTop: 15,
    textAlign: 'center',
    color: 'blue',
  },
});

export default LoginScreen;
```

### Quiz List Screen

```jsx
import React, { useEffect, useState } from 'react';
import { View, FlatList, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { getQuizzes } from '../services/quizService';
import Icon from 'react-native-vector-icons/MaterialIcons';

const QuizListScreen = ({ navigation }) => {
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchQuizzes();
  }, []);

  const fetchQuizzes = async () => {
    try {
      setLoading(true);
      const data = await getQuizzes();
      setQuizzes(data);
      setError(null);
    } catch (err) {
      setError('Failed to load quizzes. Please try again later.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const renderQuizItem = ({ item }) => (
    <TouchableOpacity 
      style={styles.quizItem}
      onPress={() => navigation.navigate('QuizDetail', { quizId: item.id })}
    >
      <View style={styles.quizContent}>
        <Text style={styles.quizTitle}>{item.title}</Text>
        <Text style={styles.quizInfo}>
          {item.questions_count} questions • {item.duration_minutes} min
        </Text>
        {item.is_public && (
          <View style={styles.publicBadge}>
            <Text style={styles.publicText}>Public</Text>
          </View>
        )}
      </View>
      <Icon name="chevron-right" size={24} color="#666" />
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#0000ff" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={fetchQuizzes}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={quizzes}
        keyExtractor={(item) => item.id}
        renderItem={renderQuizItem}
        refreshing={loading}
        onRefresh={fetchQuizzes}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No quizzes available.</Text>
        }
      />
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('CreateQuiz')}
      >
        <Icon name="add" size={24} color="#fff" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  quizItem: {
    backgroundColor: '#fff',
    padding: 16,
    marginVertical: 8,
    marginHorizontal: 16,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  quizContent: {
    flex: 1,
  },
  quizTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 4,
  },
  quizInfo: {
    color: '#666',
    fontSize: 14,
  },
  publicBadge: {
    backgroundColor: '#e0f2fe',
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 3,
    alignSelf: 'flex-start',
    marginTop: 8,
  },
  publicText: {
    color: '#0284c7',
    fontSize: 12,
    fontWeight: '600',
  },
  errorText: {
    color: '#e11d48',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#0284c7',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 5,
  },
  retryText: {
    color: '#fff',
    fontWeight: '600',
  },
  emptyText: {
    textAlign: 'center',
    padding: 20,
    color: '#666',
  },
  fab: {
    position: 'absolute',
    bottom: 16,
    right: 16,
    height: 56,
    width: 56,
    borderRadius: 28,
    backgroundColor: '#0284c7',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.5,
  },
});

export default QuizListScreen;
```

## Additional Requirements for React Native

### 1. Image Upload Setup

Install `expo-image-picker` for easy image selection from camera roll:

```bash
npm install expo-image-picker
```

### 2. QR Code Scanning

Install QR code scanning library:

```bash
npm install react-native-qrcode-scanner react-native-camera
```

### 3. Development Environment Setup

When testing with a development server, you can configure your API client differently:

```javascript
// For development IP-based testing
const API_URL = __DEV__ 
  ? 'http://192.168.1.xxx:8000/api/' // Your local IP address
  : 'https://your-production-api.com/api/';
```

## Deployment Considerations

1. SSL/TLS: Ensure your backend uses HTTPS in production
2. Update CORS settings to allow your mobile app's URL scheme
3. Use environment variables for different environments (dev/staging/prod)
4. Consider using React Native's bundled release versions for production builds
