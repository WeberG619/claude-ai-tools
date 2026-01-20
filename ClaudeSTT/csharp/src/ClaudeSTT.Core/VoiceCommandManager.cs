using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace ClaudeSTT.Core
{
    public class VoiceCommandManager
    {
        private readonly List<IVoiceCommand> _commands = new List<IVoiceCommand>();
        private readonly ISTTService _sttService;
        private ICommandContext _context;
        
        public VoiceCommandManager(ISTTService sttService)
        {
            _sttService = sttService;
            _sttService.TranscriptionReceived += OnTranscriptionReceived;
        }
        
        public void RegisterCommand(IVoiceCommand command)
        {
            _commands.Add(command);
        }
        
        public void UnregisterCommand(IVoiceCommand command)
        {
            _commands.Remove(command);
        }
        
        public void SetContext(ICommandContext context)
        {
            _context = context;
        }
        
        private void OnTranscriptionReceived(object sender, TranscriptionEventArgs e)
        {
            ProcessTranscription(e.Text);
        }
        
        private void ProcessTranscription(string transcription)
        {
            if (string.IsNullOrWhiteSpace(transcription)) return;
            
            var normalizedText = NormalizeText(transcription);
            
            foreach (var command in _commands)
            {
                if (command.CanExecute(normalizedText))
                {
                    try
                    {
                        command.Execute(normalizedText, _context);
                        _context?.LogInfo($"Executed command: {command.CommandText}");
                        break;
                    }
                    catch (Exception ex)
                    {
                        _context?.LogError($"Error executing command '{command.CommandText}': {ex.Message}");
                    }
                }
            }
        }
        
        private string NormalizeText(string text)
        {
            return Regex.Replace(text.ToLower().Trim(), @"\s+", " ");
        }
    }
    
    public abstract class BaseVoiceCommand : IVoiceCommand
    {
        public string CommandText { get; protected set; }
        public string Description { get; protected set; }
        public string[] Aliases { get; protected set; }
        
        public virtual bool CanExecute(string transcription)
        {
            var commands = new List<string> { CommandText };
            if (Aliases != null)
                commands.AddRange(Aliases);
                
            return commands.Any(cmd => 
                transcription.Contains(cmd.ToLower()) ||
                Regex.IsMatch(transcription, $@"\b{Regex.Escape(cmd.ToLower())}\b"));
        }
        
        public abstract void Execute(string transcription, ICommandContext context);
    }
    
    public class SimpleVoiceCommand : BaseVoiceCommand
    {
        private readonly Action<string, ICommandContext> _executeAction;
        
        public SimpleVoiceCommand(string command, string description, Action<string, ICommandContext> executeAction, params string[] aliases)
        {
            CommandText = command;
            Description = description;
            Aliases = aliases;
            _executeAction = executeAction;
        }
        
        public override void Execute(string transcription, ICommandContext context)
        {
            _executeAction(transcription, context);
        }
    }
}