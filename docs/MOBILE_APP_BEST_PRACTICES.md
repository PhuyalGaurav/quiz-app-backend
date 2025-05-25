# React Native Mobile App Best Practices

This guide provides best practices for developing the Quiz App mobile application using React Native.

## Project Architecture

### Recommended Folder Structure

```
src/
├── api/               # API service files
├── assets/            # Static assets like images, fonts
├── components/        # Reusable UI components
│   ├── common/        # Buttons, inputs, loaders, etc.
│   └── quiz/          # Quiz-specific components
├── config/            # Configuration files
├── context/           # Context API providers
├── hooks/             # Custom React hooks
├── navigation/        # Navigation configuration
├── screens/           # Screen components
├── store/             # State management (Redux/Context)
├── styles/            # Global styles, theme, colors
├── types/             # TypeScript type definitions
└── utils/             # Helper functions
```

## State Management

### Authentication State

Use React Context for global authentication state:

```jsx
// src/context/AuthContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as authApi from '../api/auth';

const AuthContext = createContext();

const initialState = {
  user: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,
};

function authReducer(state, action) {
  switch (action.type) {
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload,
        isLoading: false,
        error: null,
      };
    case 'LOGOUT':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        isLoading: false,
      };
    case 'AUTH_ERROR':
      return {
        ...state,
        isLoading: false,
        error: action.payload,
      };
    // Other cases...
    default:
      return state;
  }
}

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  useEffect(() => {
    // Check for tokens when app starts
    checkAuth();
  }, []);

  async function checkAuth() {
    try {
      const token = await AsyncStorage.getItem('accessToken');
      if (token) {
        const userData = await authApi.getUserProfile();
        dispatch({ type: 'LOGIN_SUCCESS', payload: userData });
      } else {
        dispatch({ type: 'LOGOUT' });
      }
    } catch (error) {
      dispatch({ type: 'AUTH_ERROR', payload: error.message });
    }
  }

  async function login(credentials) {
    try {
      const response = await authApi.login(credentials);
      await AsyncStorage.setItem('accessToken', response.access);
      await AsyncStorage.setItem('refreshToken', response.refresh);
      
      const userData = await authApi.getUserProfile();
      dispatch({ type: 'LOGIN_SUCCESS', payload: userData });
      return userData;
    } catch (error) {
      dispatch({ type: 'AUTH_ERROR', payload: error.message });
      throw error;
    }
  }

  async function logout() {
    await AsyncStorage.removeItem('accessToken');
    await AsyncStorage.removeItem('refreshToken');
    dispatch({ type: 'LOGOUT' });
  }

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
```

## API Integration Patterns

### Custom Hooks for API Calls

Create hooks for each API domain:

```jsx
// src/hooks/useQuiz.js
import { useState, useCallback } from 'react';
import * as quizApi from '../api/quiz';

export function useQuiz() {
  const [quizzes, setQuizzes] = useState([]);
  const [currentQuiz, setCurrentQuiz] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchQuizzes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await quizApi.getQuizzes();
      setQuizzes(data);
    } catch (err) {
      setError(err.message || 'Failed to load quizzes');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchQuizById = useCallback(async (quizId) => {
    try {
      setLoading(true);
      setError(null);
      const quiz = await quizApi.getQuizById(quizId);
      setCurrentQuiz(quiz);
      return quiz;
    } catch (err) {
      setError(err.message || 'Failed to load quiz details');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Other quiz-related functions...

  return {
    quizzes,
    currentQuiz,
    loading,
    error,
    fetchQuizzes,
    fetchQuizById,
    // Other functions...
  };
}
```

## Handling Images and File Uploads

### Image Processing Before Upload

```jsx
// src/utils/imageUtils.js
import * as ImageManipulator from 'expo-image-manipulator';

export async function compressImage(uri) {
  try {
    const manipulatedImage = await ImageManipulator.manipulateAsync(
      uri,
      [{ resize: { width: 1080 } }], // Resize to reasonable dimensions
      { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG }
    );
    
    return manipulatedImage.uri;
  } catch (error) {
    console.error('Error compressing image:', error);
    return uri; // Return original if compression fails
  }
}

export function createFormData(imageUri, fieldName = 'image') {
  const formData = new FormData();
  const filename = imageUri.split('/').pop();
  const match = /\.(\w+)$/.exec(filename || '');
  const type = match ? `image/${match[1]}` : 'image/jpeg';
  
  formData.append(fieldName, {
    uri: imageUri,
    name: filename || 'photo.jpg',
    type,
  });
  
  return formData;
}
```

## Handling Offline/Online State

```jsx
// src/context/NetworkContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';
import NetInfo from '@react-native-community/netinfo';

const NetworkContext = createContext({ isConnected: true });

export function NetworkProvider({ children }) {
  const [isConnected, setIsConnected] = useState(true);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsConnected(state.isConnected);
    });

    return () => unsubscribe();
  }, []);

  return (
    <NetworkContext.Provider value={{ isConnected }}>
      {children}
    </NetworkContext.Provider>
  );
}

export const useNetwork = () => useContext(NetworkContext);
```

## QR Code Scanning

```jsx
// src/screens/ScanQRScreen.js
import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { Camera } from 'expo-camera';
import { BarCodeScanner } from 'expo-barcode-scanner';
import { Button } from 'react-native-paper';

export default function ScanQRScreen({ navigation }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [scanned, setScanned] = useState(false);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  const handleBarCodeScanned = ({ data }) => {
    setScanned(true);
    
    // Check if the scanned data is a valid quiz share URL/code
    if (data.includes('/quiz/') || data.match(/^[a-zA-Z0-9]{8}$/)) {
      // Extract the share code
      const shareCode = data.includes('/quiz/') 
        ? data.split('/quiz/')[1].split('?')[0]
        : data;
        
      // Navigate to the quiz
      navigation.replace('QuizDetail', { shareCode });
    } else {
      alert('Invalid QR code. Please scan a valid quiz code.');
    }
  };

  if (hasPermission === null) {
    return <View style={styles.container}><Text>Requesting camera permission...</Text></View>;
  }
  
  if (hasPermission === false) {
    return <View style={styles.container}><Text>No access to camera.</Text></View>;
  }

  return (
    <View style={styles.container}>
      <BarCodeScanner
        onBarCodeScanned={scanned ? undefined : handleBarCodeScanned}
        style={StyleSheet.absoluteFillObject}
      />
      
      <View style={styles.overlay}>
        <Text style={styles.overlayText}>Scan Quiz QR Code</Text>
      </View>
      
      {scanned && (
        <Button 
          mode="contained" 
          onPress={() => setScanned(false)}
          style={styles.button}
        >
          Scan Again
        </Button>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'column',
    justifyContent: 'center',
  },
  overlay: {
    position: 'absolute',
    top: 50,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  overlayText: {
    fontSize: 18,
    color: 'white',
    backgroundColor: 'rgba(0,0,0,0.6)',
    padding: 16,
    borderRadius: 8,
  },
  button: {
    position: 'absolute',
    bottom: 50,
    alignSelf: 'center',
  },
});
```

## Performance Optimization

### Memoization for Components

```jsx
// Using React.memo for functional components
const QuizCard = React.memo(({ quiz, onPress }) => {
  return (
    <TouchableOpacity onPress={() => onPress(quiz.id)}>
      <Card>
        <Card.Title title={quiz.title} />
        <Card.Content>
          <Text>{quiz.questions_count} questions</Text>
        </Card.Content>
      </Card>
    </TouchableOpacity>
  );
});
```

### List Optimization

```jsx
// Optimized FlatList
<FlatList
  data={quizzes}
  keyExtractor={(item) => item.id}
  renderItem={({ item }) => (
    <QuizCard quiz={item} onPress={handleQuizPress} />
  )}
  initialNumToRender={10}
  maxToRenderPerBatch={10}
  windowSize={5}
  getItemLayout={(data, index) => ({
    length: 100, // Approximate height of each item
    offset: 100 * index,
    index,
  })}
  removeClippedSubviews={true}
/>
```

## Testing the App

### Unit Testing with Jest

```jsx
// src/screens/__tests__/LoginScreen.test.js
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import LoginScreen from '../LoginScreen';
import { AuthProvider } from '../../context/AuthContext';

// Mock the navigation prop
const mockNavigation = {
  navigate: jest.fn(),
  replace: jest.fn(),
};

// Mock API calls
jest.mock('../../api/auth', () => ({
  login: jest.fn(() => Promise.resolve({ access: 'fake-token', refresh: 'fake-refresh-token' })),
  getUserProfile: jest.fn(() => Promise.resolve({ id: 1, username: 'testuser' })),
}));

describe('LoginScreen', () => {
  it('should show validation error when fields are empty', () => {
    const { getByText, getByTestId } = render(
      <AuthProvider>
        <LoginScreen navigation={mockNavigation} />
      </AuthProvider>
    );
    
    // Find and press login button
    const loginButton = getByText('Login');
    fireEvent.press(loginButton);
    
    // Check for validation error
    expect(getByText('Please enter both username and password')).toBeTruthy();
  });
  
  it('should navigate to QuizList screen after successful login', async () => {
    const { getByTestId, getByText } = render(
      <AuthProvider>
        <LoginScreen navigation={mockNavigation} />
      </AuthProvider>
    );
    
    // Fill in the form
    fireEvent.changeText(getByTestId('username-input'), 'testuser');
    fireEvent.changeText(getByTestId('password-input'), 'password123');
    
    // Press login button
    fireEvent.press(getByText('Login'));
    
    // Verify navigation was called
    await waitFor(() => {
      expect(mockNavigation.replace).toHaveBeenCalledWith('QuizList');
    });
  });
});
```

## Security Best Practices

### Secure Storage for Tokens

```jsx
import * as SecureStore from 'expo-secure-store';

// Store tokens securely
export async function storeToken(key, value) {
  await SecureStore.setItemAsync(key, value);
}

// Retrieve stored tokens
export async function getToken(key) {
  return await SecureStore.getItemAsync(key);
}

// Delete tokens
export async function deleteToken(key) {
  await SecureStore.deleteItemAsync(key);
}
```

### Certificate Pinning for API Security

```jsx
// With Axios
import axios from 'axios';
import { Platform } from 'react-native';
import ssl from '@react-native-community/ssl-pinning';

const axiosInstance = axios.create({
  baseURL: 'https://api.example.com',
});

if (Platform.OS === 'ios' || Platform.OS === 'android') {
  axiosInstance.interceptors.request.use(config => {
    // Extract hostname from the URL
    const url = new URL(config.url, config.baseURL);
    const hostname = url.hostname;

    return new Promise((resolve, reject) => {
      ssl.fetch('https', hostname, 443, config.url, {
        method: config.method,
        headers: config.headers,
        body: config.data,
        sslPinning: {
          certs: [
            'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', // Replace with your server's certificate hash
          ],
        },
      })
      .then(response => {
        config.data = response.bodyString;
        resolve(config);
      })
      .catch(error => {
        reject(error);
      });
    });
  });
}
```

## Accessibility

```jsx
// Example of accessible component
function AccessibleButton({ onPress, label }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      accessible={true}
      accessibilityLabel={label}
      accessibilityRole="button"
      accessibilityHint={`Activates ${label}`}
    >
      <Text>{label}</Text>
    </TouchableOpacity>
  );
}
```

## Deep Linking

```jsx
// src/navigation/linking.js
const linking = {
  prefixes: ['quizapp://', 'https://quiz.example.com'],
  config: {
    screens: {
      QuizDetail: {
        path: 'quiz/:shareCode',
        parse: {
          shareCode: (shareCode) => shareCode,
        },
      },
      QuizSession: 'session/:sessionId',
      Login: 'login',
      Register: 'register',
    },
  },
};

// To handle deep links in your code:
import * as Linking from 'expo-linking';

useEffect(() => {
  const handleDeepLink = (event) => {
    const data = Linking.parse(event.url);
    if (data.path === 'quiz' && data.queryParams?.shareCode) {
      navigation.navigate('QuizDetail', { shareCode: data.queryParams.shareCode });
    }
  };

  // Listen for deep links when the app is already open
  const subscription = Linking.addEventListener('url', handleDeepLink);

  // Check for deep links that opened the app
  Linking.getInitialURL().then((url) => {
    if (url) {
      handleDeepLink({ url });
    }
  });

  return () => {
    subscription.remove();
  };
}, [navigation]);
```

By following these best practices, you'll create a well-structured, performant, and secure React Native application that integrates seamlessly with your Django backend.
