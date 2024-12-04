class VoiceChat {
    constructor() {
        this.ws = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        this.recordButton = document.getElementById('record-button');
        this.buttonText = this.recordButton.querySelector('.button-text');
        this.statusElement = document.getElementById('status');
        this.messagesContainer = document.getElementById('chat-messages');
        this.voiceActorSelect = document.getElementById('voice-actor');
        this.errorMessage = document.getElementById('error-message');
        
        this.initializeWebSocket();
        this.setupEventListeners();
    }

    initializeWebSocket() {
        const MAX_RETRIES = 3;
        let retryCount = 0;

        const connect = () => {
            this.ws = new WebSocket('ws://localhost:8000/ws');
            
            this.ws.onopen = () => {
                retryCount = 0;
                this.updateStatus('接続完了');
                this.recordButton.disabled = false;
            };
            
            this.ws.onclose = () => {
                this.updateStatus('接続が切断されました');
                this.recordButton.disabled = true;
                if (retryCount < MAX_RETRIES) {
                    retryCount++;
                    setTimeout(() => connect(), 3000);
                } else {
                    this.showError('サーバーに接続できません');
                }
            };
            
            this.ws.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.error) {
                        this.showError(data.error);
                        return;
                    }

                    // テキストメッセージを表示
                    this.addMessage(data.text, 'assistant');

                    // 音声URLが存在する場合
                    if (data.voice_url) {
                        console.log('音声URL:', data.voice_url);

                        const audioPlayer = document.getElementById('audio-player');
                        
                        // イベントリスナーを一旦すべて削除
                        audioPlayer.onplay = null;
                        audioPlayer.onended = null;
                        audioPlayer.onpause = null;
                        audioPlayer.onerror = null;

                        // 新しいイベントリスナーを設定
                        audioPlayer.addEventListener('play', () => {
                            console.log('音声再生開始');
                            this.updateStatus('音声再生中...');
                        });

                        audioPlayer.addEventListener('ended', () => {
                            console.log('音声再生終了');
                            this.updateStatus('準備完了');
                        });

                        audioPlayer.addEventListener('pause', () => {
                            console.log('音声再生一時停止');
                            this.updateStatus('準備完了');
                        });

                        audioPlayer.addEventListener('error', (e) => {
                            console.error('音声再生エラー:', e);
                            this.updateStatus('準備完了');
                            this.showError('音声の再生中にエラーが発生しました');
                        });

                        audioPlayer.src = data.voice_url;
                        audioPlayer.style.display = 'block';

                        try {
                            await audioPlayer.play();
                        } catch (playError) {
                            console.error('音声再生エラー:', playError);
                            this.showError('音声の再生に失敗しました。再生ボタンを押して再生してください。');
                            this.updateStatus('準備完了');
                        }
                    }
                } catch (error) {
                    console.error('メッセージ処理エラー:', error);
                    this.showError('メッセージの処理中にエラーが発生しました');
                    this.updateStatus('準備完了');
                }
            };
        };
        
        connect();
    }

    setupEventListeners() {
        this.recordButton.addEventListener('click', () => {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Alt') {
                event.preventDefault();
                if (!this.isRecording) {
                    this.startRecording();
                }
            }
        });

        document.addEventListener('keyup', (event) => {
            if (event.key === 'Alt') {
                event.preventDefault();
                if (this.isRecording) {
                    this.stopRecording();
                }
            }
        });
    }

    async startRecording() {
        const recognition = new webkitSpeechRecognition();
        recognition.lang = 'ja-JP';
        recognition.continuous = false;
        recognition.interimResults = false;

        this.updateRecordButtonText('音声認識中');

        recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            const message = {
                text: text,
                voice_actor_id: this.voiceActorSelect.value
            };
            this.ws.send(JSON.stringify(message));
            this.addMessage(text, 'user');
        };

        recognition.onend = () => {
            this.updateRecordButtonText('会話開始');
        };

        recognition.start();
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.isRecording = false;
            this.updateRecordButtonState();
            this.updateStatus('処理中...');
        }
    }

    async playAudio(url) {
        try {
            // URLをエンコード
            const encodedUrl = encodeURIComponent(url);
            const proxyUrl = `http://localhost:8000/proxy/audio?url=${encodedUrl}`;

            console.log('音声ファイルの取得を開始:', proxyUrl);
            const response = await fetch(proxyUrl, {
                method: 'GET',
                mode: 'cors',
                credentials: 'omit',
                headers: {
                    'Accept': 'audio/mpeg, audio/*'
                }
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('サーバーエラー:', response.status, errorText);
                
                if (response.status === 403) {
                    throw new Error('音声ファイルへのアクセスが拒否されました。しばらく待ってから再試行してください。');
                } else {
                    throw new Error(`サーバーエラー: ${response.status} - ${errorText}`);
                }
            }

            const arrayBuffer = await response.arrayBuffer();
            if (!arrayBuffer || arrayBuffer.byteLength === 0) {
                throw new Error('音声データが空です');
            }
            
            // 音声コンテキストの再開（ブラウザの自動再生ポリシーに対応）
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            console.log('音声データの解析を開始');
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            
            console.log('音声の再生を開始');
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            
            // 再生終了時のクリーンアップ
            source.onended = () => {
                console.log('音声の再生が完了');
                this.updateStatus('準備完了');
                source.disconnect();
            };
            
            source.start(0);
        } catch (error) {
            console.error('音声の再生に失敗しました:', error);
            let errorMessage = '音声の再生に失敗しました: ';
            
            if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                errorMessage += 'サーバーに接続できません。サーバーが起動しているか確認してください。';
            } else if (error.message.includes('音声ファイルへのアクセスが拒否されました')) {
                errorMessage += error.message;
            } else if (error.message.includes('The audio buffer is not valid')) {
                errorMessage += '無効な音声データです。もう一度お試しください。';
            } else if (error.message.includes('音データが空です')) {
                errorMessage += 'サーバーから音声データを取得できませんでした。もう一度お試しください。';
            } else {
                errorMessage += error.message;
            }
            
            this.showError(errorMessage);
            this.updateStatus('エラーが発生しました');
        }
    }

    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = text;
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    updateRecordButtonState() {
        this.recordButton.classList.toggle('recording', this.isRecording);
        this.buttonText.textContent = this.isRecording ? '録音停止' : '録音開始';
    }

    updateStatus(message) {
        this.statusElement.textContent = message;
    }

    showError(message) {
        console.error('エラー:', message);
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        this.errorMessage.style.backgroundColor = '#ffebee';
        this.errorMessage.style.color = '#c62828';
        this.errorMessage.style.padding = '10px';
        this.errorMessage.style.margin = '10px 0';
        this.errorMessage.style.borderRadius = '4px';
        this.errorMessage.style.border = '1px solid #ef9a9a';
        
        // エラーメッセージを20秒間表示
        setTimeout(() => {
            this.errorMessage.style.display = 'none';
        }, 20000);
    }

    updateRecordButtonText(text) {
        this.buttonText.textContent = text;
    }
}

// アプリケーションの初期化
document.addEventListener('DOMContentLoaded', () => {
    new VoiceChat();
}); 