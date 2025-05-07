# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/lgfolder/google-cloud-sdk/path.zsh.inc' ]; then . '/Users/lgfolder/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/lgfolder/google-cloud-sdk/completion.zsh.inc' ]; then . '/Users/lgfolder/google-cloud-sdk/completion.zsh.inc'; fi

export PATH="/Users/lgfolder/google-cloud-sdk/bin/gcloud:$PATH"

export PINECONE_API_KEY="c43b13df-be65-4502-b8cc-aaec71c8e56f"


# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/lgfolder/opt/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/lgfolder/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/lgfolder/opt/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/lgfolder/opt/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

export OPENAI_API_KEY_CARNIVORE=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
export OPENAI_API_KEY=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
