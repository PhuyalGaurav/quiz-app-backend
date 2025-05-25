# React Native Mobile App Integration

This guide describes how to set up your React Native mobile app to work with this Quiz API backend.

## Prerequisites

- Node.js and npm installed
- React Native development environment set up
- Knowledge of React Native and JavaScript/TypeScript

## Recommended Libraries

- **Axios** - For API requests
- **React Navigation** - For navigation and deep linking
- **AsyncStorage** - For storing tokens and user data
- **React Native Paper** - UI component library
- **Expo** - For easier development and access to native features

## Project Setup

1. Create a new React Native project:

```bash
npx react-native init QuizAppMobile
# or with Expo
expo init QuizAppMobile
```

2. Install required dependencies:

```bash
npm install axios @react-navigation/native @react-navigation/stack @react-native-async-storage/async-storage react-native-paper
npm install expo-image-picker expo-file-system expo-sharing
```

## Backend API Configuration

Create an API configuration file to connect to your backend:

```javascript
// src/config/api.js
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Change this to your server URL
export const API_BASE_URL = 'https://your-backend-url.com/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to all requests
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await AsyncStorage.getItem('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Error getting token', error);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = await AsyncStorage.getItem('refreshToken');
        const response = await axios.post(`${API_BASE_URL}/token/refresh/`, {
          refresh: refreshToken
        });
        
        await AsyncStorage.setItem('accessToken', response.data.access);
        originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
        return axios(originalRequest);
      } catch (refreshError) {
        // Handle refresh token failure - redirect to login
        await AsyncStorage.removeItem('accessToken');
        await AsyncStorage.removeItem('refreshToken');
        // Navigate to login screen here
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

## Deep Linking Setup

Configure deep linking to allow opening the app from shared quiz links:

```javascript
// app.json
{
  "expo": {
    "name": "QuizApp",
    "scheme": "quizapp",
    "slug": "quizapp",
    "version": "1.0.0",
    // ... other expo config
    "ios": {
      "bundleIdentifier": "com.yourdomain.quizapp",
      "supportsTablet": true
    },
    "android": {
      "package": "com.yourdomain.quizapp",
      "adaptiveIcon": {
        // ... adaptive icon config
      },
      "intentFilters": [
        {
          "action": "VIEW",
          "data": [
            {
              "scheme": "https",
              "host": "*.your-backend-url.com",
              "pathPrefix": "/quiz"
            },
            {
              "scheme": "quizapp"
            }
          ],
          "category": [
            "BROWSABLE",
            "DEFAULT"
          ]
        }
      ]
    }
  }
}
```

## Setting up Navigation with Deep Link Handling

```javascript
// src/navigation/AppNavigator.js
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { Linking } from 'react-native';

import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import QuizListScreen from '../screens/QuizListScreen';
import QuizDetailScreen from '../screens/QuizDetailScreen';
import QuizSessionScreen from '../screens/QuizSessionScreen';
import ResultScreen from '../screens/ResultScreen';
import CreateQuizScreen from '../screens/CreateQuizScreen';
import ScanQRScreen from '../screens/ScanQRScreen';

const Stack = createStackNavigator();

const linking = {
  prefixes: ['quizapp://', 'https://your-backend-url.com'],
  config: {
    screens: {
      QuizDetail: {
        path: 'quiz/:shareCode',
        parse: {
          shareCode: (shareCode) => `${shareCode}`,
        },
      },
    },
  },
};

const AppNavigator = () => {
  return (
    <NavigationContainer linking={linking}>
      <Stack.Navigator>
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Register" component={RegisterScreen} />
        <Stack.Screen name="QuizList" component={QuizListScreen} options={{ title: 'Quizzes' }} />
        <Stack.Screen name="QuizDetail" component={QuizDetailScreen} options={{ title: 'Quiz Details' }} />
        <Stack.Screen name="QuizSession" component={QuizSessionScreen} options={{ title: 'Quiz Session', headerShown: false }} />
        <Stack.Screen name="Result" component={ResultScreen} options={{ title: 'Quiz Results', headerLeft: null }} />
        <Stack.Screen name="CreateQuiz" component={CreateQuizScreen} options={{ title: 'Create Quiz' }} />
        <Stack.Screen name="ScanQR" component={ScanQRScreen} options={{ title: 'Scan QR Code' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;
```

## Authentication Screens

### Login Screen

```javascript
// src/screens/LoginScreen.js
import React, { useState } from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { TextInput, Button, Text, Card } from 'react-native-paper';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../config/api';

const LoginScreen = ({ navigation }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!username || !password) {
      setError('Please enter both username and password');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const response = await api.post('/token/', {
        username,
        password,
      });

      // Store tokens
      await AsyncStorage.setItem('accessToken', response.data.access);
      await AsyncStorage.setItem('refreshToken', response.data.refresh);
      
      // Navigate to main app
      navigation.replace('QuizList');
    } catch (err) {
      console.error('Login error:', err.response?.data || err.message);
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Card style={styles.card}>
        <Card.Title title="Quiz App" />
        <Card.Content>
          <TextInput
            label="Username"
            value={username}
            onChangeText={setUsername}
            mode="outlined"
            style={styles.input}
            autoCapitalize="none"
          />
          <TextInput
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            mode="outlined"
            style={styles.input}
          />
          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          <Button
            mode="contained"
            onPress={handleLogin}
            loading={loading}
            style={styles.button}
          >
            Login
          </Button>
          <TouchableOpacity onPress={() => navigation.navigate('Register')}>
            <Text style={styles.linkText}>Don't have an account? Register here</Text>
          </TouchableOpacity>
        </Card.Content>
      </Card>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
  },
  card: {
    padding: 16,
  },
  input: {
    marginBottom: 16,
  },
  button: {
    marginTop: 8,
    marginBottom: 16,
  },
  errorText: {
    color: 'red',
    marginBottom: 8,
  },
  linkText: {
    textAlign: 'center',
    color: '#0066cc',
  },
});

export default LoginScreen;
```

### Quiz Detail with QR Code Sharing

```javascript
// src/screens/QuizDetailScreen.js
import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Share, Image } from 'react-native';
import { Card, Text, Button, ActivityIndicator, Divider } from 'react-native-paper';
import api from '../config/api';
import { API_BASE_URL } from '../config/api';

const QuizDetailScreen = ({ route, navigation }) => {
  const { quizId, shareCode } = route.params;
  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [qrCode, setQrCode] = useState(null);

  useEffect(() => {
    fetchQuizDetails();
  }, []);

  const fetchQuizDetails = async () => {
    try {
      setLoading(true);
      let response;
      
      if (quizId) {
        response = await api.get(`/quizzes/${quizId}/`);
      } else if (shareCode) {
        response = await api.get(`/join/${shareCode}/`);
      } else {
        setError('No quiz identifier provided');
        return;
      }
      
      setQuiz(response.data);
      
      // Also fetch QR code if available
      if (response.data.id) {
        try {
          const qrResponse = await api.get(`/quizzes/${response.data.id}/qr_code/`);
          setQrCode(qrResponse.data.qr_code);
        } catch (qrError) {
          console.log('QR code not available:', qrError);
        }
      }
    } catch (err) {
      console.error('Error fetching quiz:', err);
      setError('Failed to load quiz details. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleShare = async () => {
    if (!quiz) return;
    
    try {
      const shareUrl = `https://your-backend-url.com/quiz/${quiz.share_code}`;
      await Share.share({
        message: `Join my quiz: "${quiz.title}" - ${shareUrl}`,
        url: shareUrl,
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const startQuiz = async () => {
    try {
      setLoading(true);
      const response = await api.post('/sessions/', { quiz: quiz.id });
      navigation.navigate('QuizSession', { sessionId: response.data.id, quizTitle: quiz.title });
    } catch (err) {
      console.error('Error starting quiz:', err);
      setError('Failed to start quiz. Please try again.');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#0066cc" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>{error}</Text>
        <Button mode="contained" onPress={fetchQuizDetails} style={styles.button}>
          Retry
        </Button>
      </View>
    );
  }

  if (!quiz) {
    return (
      <View style={styles.centered}>
        <Text>Quiz not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.title}>{quiz.title}</Text>
          {quiz.description ? (
            <Text style={styles.description}>{quiz.description}</Text>
          ) : null}
          
          <Divider style={styles.divider} />
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Questions:</Text>
            <Text style={styles.infoValue}>{quiz.questions_count}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Time Limit:</Text>
            <Text style={styles.infoValue}>{quiz.duration_minutes} minutes</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Created By:</Text>
            <Text style={styles.infoValue}>{quiz.creator?.username || 'Unknown'}</Text>
          </View>

          {quiz.is_public && (
            <View style={styles.publicBadge}>
              <Text style={styles.publicText}>Public Quiz</Text>
            </View>
          )}
          
          {qrCode && (
            <View style={styles.qrContainer}>
              <Text style={styles.qrTitle}>Share via QR Code:</Text>
              <Image source={{ uri: qrCode }} style={styles.qrImage} />
            </View>
          )}

          <View style={styles.buttonContainer}>
            <Button mode="contained" onPress={startQuiz} style={styles.button}>
              Start Quiz
            </Button>
            
            <Button 
              mode="outlined" 
              onPress={handleShare} 
              style={styles.button}
              icon="share"
            >
              Share Quiz
            </Button>
          </View>
        </Card.Content>
      </Card>
    </ScrollView>
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
  card: {
    margin: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  description: {
    fontSize: 16,
    color: '#555',
    marginBottom: 16,
  },
  divider: {
    marginVertical: 16,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 16,
    color: '#555',
  },
  infoValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  buttonContainer: {
    marginTop: 24,
  },
  button: {
    marginVertical: 8,
  },
  errorText: {
    color: 'red',
    marginBottom: 16,
    textAlign: 'center',
  },
  publicBadge: {
    backgroundColor: '#e6f7ff',
    padding: 8,
    borderRadius: 4,
    alignSelf: 'flex-start',
    marginTop: 16,
  },
  publicText: {
    color: '#0066cc',
    fontWeight: '600',
  },
  qrContainer: {
    alignItems: 'center',
    marginTop: 24,
    marginBottom: 16,
  },
  qrTitle: {
    fontSize: 16,
    marginBottom: 12,
    fontWeight: '600',
  },
  qrImage: {
    width: 200,
    height: 200,
  },
});

export default QuizDetailScreen;
```

## Additional Mobile-Specific Features

- **Camera Integration**: Allow taking photos of quiz questions directly from the app
- **Offline Mode**: Store quiz data locally for offline access
- **Push Notifications**: Send reminders for quizzes or notify when a quiz is shared with a user
- **Biometric Authentication**: Add fingerprint or face recognition for enhanced security

## Push Notifications Setup

For push notifications on mobile devices, you'll need to update your backend to store device tokens:

1. Add a model for device tokens in your Django backend
2. Configure a notification service like Firebase Cloud Messaging (FCM)
3. Set up the React Native app to receive notifications

## Testing Mobile Integration

1. Run your Django backend on a local network or deploy to a test environment
2. Configure your React Native app to point to the correct backend URL
3. Test all API endpoints using Postman or another API testing tool
4. Use tools like React Native Debugger to monitor API calls and responses

With this setup, your mobile app will be able to communicate seamlessly with your Django backend API.
