import React, { useState } from 'react';
import axios from 'axios';
import './Chatbot.css'; // Ensure this path is correct

const Chatbot = () => {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState('');

  const askQuestion = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('http://127.0.0.1:8000/ask', {
        question: question
      });
      if (Array.isArray(res.data.result) && res.data.result.length > 0) {
        setResponse(res.data.result[0][0]); // Extract the number
      } else {
        setResponse("No valid response received.");
      }
    } catch (error) {
      setResponse("Error connecting to server");
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">Chatbot</div>
      <div className="chatbot-body">
        <form className="chatbot-form" onSubmit={askQuestion}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question..."
            className="chatbot-input"
          />
          <button type="submit" className="chatbot-button">Ask</button>
        </form>
        {response && <div className="chatbot-response">Response: {response}</div>} {/* Display the number directly */}
      </div>
    </div>
  );
};

export default Chatbot;
