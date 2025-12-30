
import argparse
import numpy as np
import os

import pandas as pd
import tensorflow as tf

from google.cloud import bigquery
from google.cloud import storage

# Read environmental variables
training_data_uri = os.getenv("AIP_TRAINING_DATA_URI")
validation_data_uri = os.getenv("AIP_VALIDATION_DATA_URI")
test_data_uri = os.getenv("AIP_TEST_DATA_URI")

# Read args
parser = argparse.ArgumentParser()
parser.add_argument('--label_column', required=True, type=str)
parser.add_argument('--epochs', default=10, type=int)
parser.add_argument('--batch_size', default=10, type=int)
args = parser.parse_args()

# Set up training variables
LABEL_COLUMN = args.label_column

# See https://cloud.google.com/vertex-ai/docs/workbench/managed/executor#explicit-project-selection for issues regarding permissions.
PROJECT_NUMBER = os.environ["CLOUD_ML_PROJECT_ID"]
bq_client = bigquery.Client(project=PROJECT_NUMBER)


# Download a table
def download_table(bq_table_uri: str):
    # Remove bq:// prefix if present
    prefix = "bq://"
    if bq_table_uri.startswith(prefix):
        bq_table_uri = bq_table_uri[len(prefix) :]
        
    # Download the BigQuery table as a dataframe
    # This requires the "BigQuery Read Session User" role on the custom training service account.
    table = bq_client.get_table(bq_table_uri)
    return bq_client.list_rows(table).to_dataframe()

# Download dataset splits
df_train = download_table(training_data_uri)
df_validation = download_table(validation_data_uri)
df_test = download_table(test_data_uri)

def convert_dataframe_to_dataset(
    df_train: pd.DataFrame,
    df_validation: pd.DataFrame,
):
    df_train_x, df_train_y = df_train, df_train.pop(LABEL_COLUMN)
    df_validation_x, df_validation_y = df_validation, df_validation.pop(LABEL_COLUMN)

    y_train = tf.convert_to_tensor(np.asarray(df_train_y).astype("float32"))
    y_validation = tf.convert_to_tensor(np.asarray(df_validation_y).astype("float32"))

    # Convert to numpy representation
    x_train = tf.convert_to_tensor(np.asarray(df_train_x).astype("float32"))
    x_test = tf.convert_to_tensor(np.asarray(df_validation_x).astype("float32"))

    # Convert to one-hot representation
    num_species = len(df_train_y.unique())
    y_train = tf.keras.utils.to_categorical(y_train, num_classes=num_species)
    y_validation = tf.keras.utils.to_categorical(y_validation, num_classes=num_species)

    dataset_train = tf.data.Dataset.from_tensor_slices((x_train, y_train))
    dataset_validation = tf.data.Dataset.from_tensor_slices((x_test, y_validation))
    return (dataset_train, dataset_validation)

# Create datasets
dataset_train, dataset_validation = convert_dataframe_to_dataset(df_train, df_validation)

# Shuffle train set
dataset_train = dataset_train.shuffle(len(df_train))

def create_model(num_features):
    # Create model
    Dense = tf.keras.layers.Dense
    model = tf.keras.Sequential(
        [
            Dense(
                100,
                activation=tf.nn.relu,
                kernel_initializer="uniform",
                input_dim=num_features,
            ),
            Dense(75, activation=tf.nn.relu),
            Dense(50, activation=tf.nn.relu),            
            Dense(25, activation=tf.nn.relu),
            Dense(3, activation=tf.nn.softmax),
        ]
    )
    
    # Compile Keras model
    optimizer = tf.keras.optimizers.RMSprop(lr=0.001)
    model.compile(
        loss="categorical_crossentropy", metrics=["accuracy"], optimizer=optimizer
    )
    
    return model

# Create the model
model = create_model(num_features=dataset_train._flat_shapes[0].dims[0].value)

# Set up datasets
dataset_train = dataset_train.batch(args.batch_size)
dataset_validation = dataset_validation.batch(args.batch_size)

# Train the model
model.fit(dataset_train, epochs=args.epochs, validation_data=dataset_validation)

tf.saved_model.save(model, os.getenv("AIP_MODEL_DIR"))
