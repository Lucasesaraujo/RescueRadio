import { Component, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

type RescueRadioEvent = {
  type: string;
  channel_id?: string;
  usuario?: string;
  message?: string;
  messages?: RescueRadioMessage[];
  members?: { usuario: string; status: string }[];
  payload?: RescueRadioMessage;
};

type RescueRadioMessage = {
  type: string;
  usuario: string;
  timestamp_iso: string;
  corpo_texto: string;
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  username = '';
  messageText = '';
  channelId = 'canal-geral';

  socket: WebSocket | null = null;

  connected = false;
  connectionStatus = 'Desconectado';

  messages: RescueRadioMessage[] = [];
  systemEvents: string[] = [];
  members: { usuario: string; status: string }[] = [];

  constructor(
    private zone: NgZone,
    private cdr: ChangeDetectorRef
  ) {}

  connect(): void {
    const cleanedUsername = this.username.trim();

    if (!cleanedUsername) {
      alert('Informe seu nome antes de entrar no canal.');
      return;
    }

    const url = `ws://localhost:8000/ws/channel/${this.channelId}?usuario=${encodeURIComponent(cleanedUsername)}`;

    this.socket = new WebSocket(url);
    this.connectionStatus = 'Conectando...';

    this.socket.onopen = () => {
      this.updateView(() => {
        this.connected = true;
        this.connectionStatus = 'Conectado';
        this.addSystemEvent(`${cleanedUsername} conectado ao canal.`);
      });
    };

    this.socket.onmessage = (event) => {
      this.updateView(() => {
        const data: RescueRadioEvent = JSON.parse(event.data);
        this.handleSocketEvent(data);
      });
    };

    this.socket.onerror = () => {
      this.updateView(() => {
        this.connectionStatus = 'Erro de conexão';
        this.addSystemEvent('Erro na conexão com o canal.');
      });
    };

    this.socket.onclose = () => {
      this.updateView(() => {
        this.connected = false;
        this.connectionStatus = 'Desconectado';
        this.addSystemEvent('Conexão encerrada.');
      });
    };
  }

  disconnect(): void {
    this.socket?.close();
    this.socket = null;
  }

  sendMessage(): void {
    const text = this.messageText.trim();

    if (!text || !this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }

    const message: RescueRadioMessage = {
      type: 'SEND_MESSAGE',
      usuario: this.username,
      timestamp_iso: new Date().toISOString(),
      corpo_texto: text,
    };

    this.socket.send(JSON.stringify(message));
    this.messageText = '';
  }

  private handleSocketEvent(event: RescueRadioEvent): void {
    switch (event.type) {
      case 'CONNECTED':
        this.addSystemEvent(event.message ?? 'Conectado ao canal.');
        break;

      case 'BRIEFING':
        this.messages = event.messages ?? [];
        this.addSystemEvent(`Briefing recebido com ${this.messages.length} mensagem(ns).`);
        break;

      case 'MESSAGE_RECEIVED':
        if (event.payload) {
          this.messages.push(event.payload);
        }
        break;

      case 'MEMBER_JOINED':
        this.members = event.members ?? this.members;
        this.addSystemEvent(event.message ?? `${event.usuario} entrou no canal.`);
        break;

      case 'MEMBER_LEFT':
        this.members = event.members ?? this.members;
        this.addSystemEvent(event.message ?? `${event.usuario} saiu do canal.`);
        break;

      case 'ERROR':
        this.addSystemEvent(`Erro: ${event.message}`);
        break;

      default:
        this.addSystemEvent(`Evento desconhecido: ${event.type}`);
        break;
    }
  }

  private addSystemEvent(message: string): void {
    const timestamp = new Date().toLocaleTimeString();
    this.systemEvents.push(`[${timestamp}] ${message}`);
  }

  private updateView(callback: () => void): void {
    this.zone.run(() => {
      callback();
      this.cdr.detectChanges();
    });
  }
}