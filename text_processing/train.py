import numpy as np
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from .nlp_utils import bag_of_words, tokenize, stem, ignore_words
from .nlp_model import NeuralNet


class ChatDataset(Dataset):
    def __init__(self, X_train, Y_train):
        self.n_samples = len(X_train)
        self.x_data = X_train
        self.y_data = Y_train

    def __getitem__(self, index):
        return self.x_data[index], self.y_data[index]

    def __len__(self):
        return self.n_samples


def collect_training_data(fp_to_intents: str):
    with open(fp_to_intents, 'r') as f:
        intents = json.load(f)

    all_words = []
    tags = []
    xy = []
    for intent in intents['intents']:
        tags.append(intent['tag'])
        for pattern in intent['patterns']:
            w = tokenize(pattern)
            all_words.extend(w)
            xy.append((w, intent["tag"]))

    all_words = [stem(word) for word in all_words if word not in ignore_words]

    all_words = sorted(set(all_words))
    tags = sorted(set(tags))

    return all_words, tags, xy


def train_model(fp_to_model: str, fp_to_intents: str):
    all_words, tags, xy = collect_training_data(fp_to_intents)

    X_train = []
    y_train = []
    for (pattern_sentence, tag) in xy:
        bag = bag_of_words(pattern_sentence, all_words)
        label = tags.index(tag)

        X_train.append(bag)
        y_train.append(label)

    X_train = np.array(X_train)
    y_train = np.array(y_train)

    num_epochs = 1000
    batch_size = 8
    learning_rate = 0.001
    input_size = len(X_train[0])
    hidden_size = 8
    output_size = len(tags)

    dataset = ChatDataset(X_train, y_train)
    train_loader = DataLoader(dataset=dataset,
                              batch_size=batch_size,
                              shuffle=True,
                              num_workers=0)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = NeuralNet(input_size, hidden_size, output_size).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    for epoch in range(num_epochs):
        for (words, labels) in train_loader:
            words = words.to(device)
            labels = labels.to(dtype=torch.long).to(device)

            outputs = model(words)
            loss = criterion(outputs, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    data = {
        "model_state": model.state_dict(),
        "input_size": input_size,
        "hidden_size": hidden_size,
        "output_size": output_size,
        "all_words": all_words,
        "tags": tags
    }

    torch.save(data, fp_to_model)
    print(f'training complete. file saved to {fp_to_model}')
