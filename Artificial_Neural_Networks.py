
# coding: utf-8

# # <center>Time Series Analysis on Pune precipitation data from 1965 to 2002.</center>

# In[8]:


import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
get_ipython().run_line_magic('matplotlib', 'inline')

import math
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Flatten
from keras.layers.convolutional import Conv1D
from keras.layers.convolutional import MaxPooling1D
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error

from IPython.display import SVG
from keras.utils.vis_utils import model_to_dot

import itertools
import warnings
warnings.filterwarnings('ignore')


# In[73]:


#filename = 'pune_1965_to_2002.csv'
#STORAGE_FOLDER = 'output/'


# In[78]:


def preprocess_data(filename):
    rainfall_data_matrix = pd.read_csv(filename, delimiter='\t')
    rainfall_data_matrix.set_index('Year', inplace=True)
    rainfall_data_matrix = rainfall_data_matrix.transpose()
    dates = pd.date_range(start='1901-01', freq='MS', periods=len(rainfall_data_matrix.columns)*12)
    
    rainfall_data_matrix_np = rainfall_data_matrix.transpose().as_matrix()
    shape = rainfall_data_matrix_np.shape
    rainfall_data_matrix_np = rainfall_data_matrix_np.reshape((shape[0] * shape[1], 1))
    
    rainfall_data = pd.DataFrame({'Precipitation': rainfall_data_matrix_np[:,0]})
    rainfall_data.set_index(dates, inplace=True)

    test_rainfall_data = rainfall_data.ix['1998': '2002']
    rainfall_data = rainfall_data.ix[: '1998']
    rainfall_data = rainfall_data.round(5)
    
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(rainfall_data)
    
    return rainfall_data, test_rainfall_data, scaler


# In[72]:


# FILENAME = 'pune_1965_to_2002.csv'
# rainfall_data, test_rainfall_data, scaler = preprocess_data(FILENAME)


# ## <center> Artificial Neural Networks </center>

# In[12]:


from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error

def mean_absolute_percentage_error(y_true, y_pred): 
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def root_mean_squared_error(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    return rmse


# In[13]:


def calculate_performance(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    return round(mse, 3), round(mae, 3), round(mape, 3), round(rmse, 3)


# In[14]:


def plot_keras_model(model, show_shapes=True, show_layer_names=True):
    return SVG(model_to_dot(model, show_shapes=show_shapes, show_layer_names=show_layer_names).create(prog='dot',format='svg'))


# In[15]:


def get_combinations(parameters):
    return list(itertools.product(*parameters))


# In[16]:


def create_NN(input_nodes, hidden_nodes, output_nodes):
    model = Sequential()
    model.add(Dense(int(hidden_nodes), input_dim=int(input_nodes)))
    model.add(Dense(int(output_nodes)))
    model.compile(loss='mean_squared_error', optimizer='adam')
    return model


# In[17]:


def train_model(model, X_train, y_train, epochs, batch_size):
    model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=0, shuffle=True)
    return model


# In[18]:


def reshape_arrays(X_train, y_train):
    X_train = np.array(X_train)
    y_train = np.reshape(y_train, (len(y_train), 1))
    return X_train, y_train


# In[19]:


def preprocess_WNN(data, look_back):
    data = np.array(data)[:, 0]
    X_train = []
    y_train = []
    for i in range(data.shape[0]-look_back):
        x = data[i:look_back+i][::-1]
        y = data[look_back+i]
        X_train.append(list(x))
        y_train.append(y)
    input_seq_for_test = data[i+1:look_back+i+1][::-1]
    return X_train, y_train, input_seq_for_test


# In[20]:


def forecast_WNN(model, input_sequence, future_steps):
    forecasted_values = []
    for i in range(future_steps):
        forecasted_value = model.predict(input_sequence)
        if forecasted_value < 0:
            forecasted_value = forecasted_value - forecasted_value
        forecasted_values.append(forecasted_value[0][0])
        input_sequence[0] = np.append(forecasted_value, input_sequence[0][:-1])
    return forecasted_values


# In[21]:


def WNN(data, look_back, hidden_nodes, output_nodes, epochs, batch_size, future_steps, scaler):
    data = scaler.transform(data)
    X_train, y_train, input_seq_for_test_WNN = preprocess_WNN(data, look_back)
    X_train, y_train = reshape_arrays(X_train, y_train)

    model_WNN = create_NN(input_nodes=look_back, hidden_nodes=hidden_nodes, output_nodes=output_nodes)
    model_WNN = train_model(model_WNN, X_train, y_train, epochs, batch_size)

    input_seq_for_test_WNN = np.reshape(input_seq_for_test_WNN, (1, len(input_seq_for_test_WNN)))
    forecasted_values_WNN = forecast_WNN(model_WNN, input_sequence=input_seq_for_test_WNN, future_steps=future_steps)
    
    forecasted_values_WNN = list(scaler.inverse_transform([forecasted_values_WNN])[0])
    print(forecasted_values_WNN)
    return model_WNN, forecasted_values_WNN


# In[22]:


def get_accuracies_WNN(rainfall_data, test_rainfall_data, parameters, scaler):
    combination_of_params = get_combinations(parameters)
    information_WNN = []
    iterator = 0
    print('WNN - Number of combinations: ' + str(len(combination_of_params)))
    
    for param in combination_of_params:
        if (iterator+1) != len(combination_of_params):
            print(iterator+1, end=' -> ')
        else:
            print(iterator+1)
        iterator = iterator+1

        look_back = param[0]
        hidden_nodes = param[1]
        output_nodes = param[2]
        epochs = param[3]
        batch_size = param[4]
        future_steps = param[5]

        model_WNN, forecasted_values_WNN = WNN(rainfall_data, look_back, hidden_nodes, output_nodes, epochs, batch_size, future_steps, scaler)
        
        y_true = test_rainfall_data.ix[:future_steps].Precipitation
        mse, mae, mape, rmse = calculate_performance(y_true, forecasted_values_WNN)
        
        info = list(param) + [mse, mae, rmse] + forecasted_values_WNN
        information_WNN.append(info)

    information_WNN_df = pd.DataFrame(information_WNN)
    indexes = [str(i) for i in list(range(1, future_steps+1))]
    information_WNN_df.columns = ['look_back', 'hidden_nodes', 'output_nodes', 'epochs', 'batch_size', 'future_steps', 'MSE', 'MAE', 'RMSE'] + indexes
    return information_WNN_df


# In[23]:




# In[27]:


def preprocess_WAANN(data, seasonal_period):
    data = np.array(data)[:, 0]
    X_train = []
    y_train = []
    for i in range(seasonal_period, data.shape[0]-seasonal_period+1):
        x = data[i-seasonal_period:i][::-1]
        y = data[i:i+seasonal_period]
        X_train.append(list(x))
        y_train.append(list(y))
    input_seq_for_test = data[i+1-seasonal_period:i+1][::-1]
    return X_train, y_train, input_seq_for_test


# In[28]:


def forecast_WAANN(model, input_sequence, seasonal_period, future_steps):
    iterations = future_steps/seasonal_period
    forecasted_values = []
    for i in range(int(iterations) + 1):
        next_forecasted_values = model.predict(input_sequence)
        forecasted_values += list(next_forecasted_values[0])
        input_sequence = next_forecasted_values
    return forecasted_values[:future_steps]


# In[29]:


def WAANN(data, seasonal_period, hidden_nodes, epochs, batch_size, future_steps, scaler):
    data = scaler.transform(data)
    X_train, y_train, input_seq_for_test_WAANN = preprocess_WAANN(data, seasonal_period)
    X_train = np.array(X_train)
    y_train = np.array(y_train)

    input_seq_for_test_WAANN = np.reshape(input_seq_for_test_WAANN, (1, len(input_seq_for_test_WAANN)))
    model_WAANN = create_NN(input_nodes=seasonal_period, hidden_nodes=hidden_nodes, output_nodes=seasonal_period)
    model_WAANN = train_model(model_WAANN, X_train, y_train, epochs, batch_size)
    
    forecasted_values_WAANN = forecast_WAANN(model_WAANN, input_seq_for_test_WAANN, seasonal_period, future_steps=future_steps)
    forecasted_values_WAANN = list(scaler.inverse_transform([forecasted_values_WAANN])[0])
    print(forecasted_values_WAANN)
    return model_WAANN, forecasted_values_WAANN


# In[30]:


def get_accuracies_WAANN(rainfall_data, test_rainfall_data, parameters, scaler):
    combination_of_params = get_combinations(parameters)
    information_WAANN = []
    iterator = 0
    print('WAANN - Number of combinations: ' + str(len(combination_of_params)))
    
    for param in combination_of_params:
        if (iterator+1) != len(combination_of_params):
            print(iterator+1, end=' -> ')
        else:
            print(iterator+1)
        iterator = iterator+1

        seasonal_period = param[0]
        hidden_nodes = param[1]
        epochs = param[2]
        batch_size = param[3]
        future_steps = param[4]

        model_WAANN, forecasted_values_WAANN = WAANN(rainfall_data, seasonal_period, hidden_nodes, epochs, batch_size, future_steps, scaler)
        
        y_true = test_rainfall_data.ix[:future_steps].Precipitation
        mse, mae, mape, rmse = calculate_performance(y_true, forecasted_values_WAANN)
        
        info = list(param) + [mse, mae, rmse] + forecasted_values_WAANN
        information_WAANN.append(info)

    information_WAANN_df = pd.DataFrame(information_WAANN)
    indexes = [str(i) for i in list(range(1, future_steps+1))]
    information_WAANN_df.columns = ['seasonal_period', 'hidden_nodes', 'epochs', 'batch_size', 'future_steps', 'MSE', 'MAE', 'RMSE'] + indexes
    return information_WAANN_df


# In[31]:



def analyze_results(data_frame, test_rainfall_data, name, STORAGE_FOLDER, flag=False):
    optimized_params = data_frame.iloc[data_frame.RMSE.argmin]
    future_steps = optimized_params.future_steps
    forecast_values = optimized_params[-1*int(future_steps):]
    y_true = test_rainfall_data.ix[:int(future_steps)]
    forecast_values.index = y_true.index
        
    print('=== Best parameters of ' + name + ' ===\n')
    if (name == 'WNN'):
        model = create_NN(optimized_params.look_back, 
                          optimized_params.hidden_nodes, 
                          optimized_params.output_nodes)
        print('Input nodes(p): ' + str(optimized_params.look_back))
        print('Hidden nodes: ' + str(optimized_params.hidden_nodes))
        print('Output nodes: ' + str(optimized_params.output_nodes))
        
    elif (name == 'WAANN'):
        model = create_NN(optimized_params.seasonal_period, 
                          optimized_params.hidden_nodes, 
                          optimized_params.seasonal_period)
        print('Input nodes(s): ' + str(optimized_params.seasonal_period))
        print('Hidden nodes: ' + str(optimized_params.hidden_nodes))
        print('Output nodes: ' + str(optimized_params.seasonal_period))
    elif (name == 'CNN'):
        model = create_CNN(optimized_params.look_back,
                           optimized_params.filters,
                           optimized_params.output_nodes)
        print('Input nodes(s): ' + str(optimized_params.look_back))
        print('Filters: ' + str(optimized_params.filters))
        print('Output nodes: ' + str(optimized_params.output_nodes))
        
    print('Number of epochs: ' + str(optimized_params.epochs))
    print('Batch size: ' + str(optimized_params.batch_size))
    print('Number of future steps forecasted: ' + str(optimized_params.future_steps))
    print('Mean Squared Error(MSE): ' + str(optimized_params.MSE))
    print('Mean Absolute Error(MAE): ' + str(optimized_params.MAE))
    print('Root Mean Squared Error(RMSE): ' + str(optimized_params.RMSE))
    print('\n\n')
    
    # Save model
    from keras.utils import plot_model
    plot_model(model, to_file = STORAGE_FOLDER + name + '_best_fit_model.png', show_shapes=True, show_layer_names=True)
    
    # Save data
    data_frame.to_csv(STORAGE_FOLDER + name + '_information.csv')
    optimized_params.to_csv(STORAGE_FOLDER + name + '_optimized_values.csv')
    
    # Actual and forecasted values
    errors = test_rainfall_data.Precipitation - forecast_values
    actual_forecast = pd.DataFrame({'Actual': test_rainfall_data.Precipitation, 'Forecasted': forecast_values, 
                                    'Errors': errors})
    actual_forecast.to_csv(STORAGE_FOLDER + name + '_actual_and_forecasted.csv')
    
    plt.figure(figsize=(10,5))
    plt.plot(actual_forecast.drop(columns=['Actual', 'Forecasted']), color='blue', label='Error: Actual - Forecasted')
    plt.xlabel('Year')
    plt.ylabel('Error')
    plt.legend(loc='best')
    plt.title(name + ' - Error: Actual - Forecasted')
    plt.savefig(STORAGE_FOLDER + name + '_error_plot'  + '.png')
    
    
    plt.figure(figsize=(10,5))
    plt.plot(y_true, color='green', label='Actual values')
    plt.plot(forecast_values, color='red', label='Forecasted values')
    plt.xlabel('Year')
    plt.ylabel('Monthly mean Precipitation')
    plt.legend(loc='best')
    if (flag==False):
        plt.title(name + ' - Comaprison: Actual vs Forecasted')
        plt.savefig(STORAGE_FOLDER + name + '_best_forecast'  + '.png')
    else:
        plt.title('Best of all: ' + name + ' - Comaprison: Actual vs Forecasted')
        plt.savefig(STORAGE_FOLDER + 'BEST_FORECAST_' + name + '.png')
    
    return optimized_params


# In[48]:


def best_of_all(list_of_methods):
    RMSE_values = [x.RMSE for x in list_of_methods]
    index = np.argmin(RMSE_values)
    if (index == 0):
        name = 'WNN'
    
    elif (index == 1):
        name = 'WAANN'
    
    else:
        name = 'CNN'
    print(RMSE_values)
    
    names = ['WNN', 'WAANN']
    RMSE_info = pd.Series(RMSE_values, index=names)
    
    print('Overall Best method on this data is ' + name)
    return index, name, RMSE_info


# In[49]:


def compare_ANN_methods(rainfall_data, test_rainfall_data, scaler, parameters_WNN, parameters_TLNN, 
                        parameters_WAANN, parameters_LSTM, future_steps, STORAGE_FOLDER):
    
    information_WNN_df = get_accuracies_WNN(rainfall_data, test_rainfall_data, parameters_WNN, scaler)
    optimized_params_WNN = analyze_results(information_WNN_df, test_rainfall_data, 'WNN', STORAGE_FOLDER)
    
      
    information_WAANN_df = get_accuracies_WAANN(rainfall_data, test_rainfall_data, parameters_WAANN, scaler)
    optimized_params_WAANN = analyze_results(information_WAANN_df, test_rainfall_data, 'WAANN', STORAGE_FOLDER)
    
    list_of_methods = [optimized_params_WNN, optimized_params_WAANN]
    information = [information_WNN_df, information_WAANN_df]
    index, name, RMSE_info = best_of_all(list_of_methods)
    best_optimized_params = analyze_results(information[index], test_rainfall_data, name, STORAGE_FOLDER, True)
    return RMSE_info


# In[69]:


def save_RMSE_info(STORAGE_FOLDER, RMSE_info):
    
    
    RMSE_df = pd.DataFrame({'RMSE': RMSE_info})
    RMSE_df.index = RMSE_info.index
    RMSE_df.to_csv(STORAGE_FOLDER + 'RMSE_score.csv')
    
    axis = RMSE_info.plot(kind='bar', figsize=(10,5), rot=0, title='RMSE scores')
    for p in axis.patches:
        axis.annotate(np.round(p.get_height(),decimals=2), 
                    (p.get_x()+p.get_width()/2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 10), 
                    textcoords='offset points', fontsize=14, color='black')

    fig = axis.get_figure()
    fig.savefig(STORAGE_FOLDER + 'RMSE.png')


# In[79]:


# STORAGE_FOLDER = 'output/'
future_steps = 60


# In[80]:


# look_back, hidden_nodes, output_nodes, epochs, batch_size, future_steps
parameters_WNN = [[1,2,3,6,8,10,12], [3,4,5,6], [1], [500], [20], [future_steps]]
parameters_WNN = [[12], [4], [1], [500], [20], [future_steps]]


# seasonal_period, hidden_nodes, epochs, batch_size, future_steps
parameters_WAANN = [[12], [3,4,5,6,7,8,9,10], [500], [20], [future_steps]]
parameters_WAANN = [[12], [3], [500], [20], [future_steps]]

# RMSE_info = compare_ANN_methods(rainfall_data, test_rainfall_data, scaler, 
#                    parameters_WNN, parameters_TLNN, parameters_WAANN, parameters_LSTM, future_steps, STORAGE_FOLDER)


# In[76]:


# save_RMSE_info(STORAGE_FOLDER, RMSE_info)

