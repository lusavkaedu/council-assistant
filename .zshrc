# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/lgfolder/google-cloud-sdk/path.zsh.inc' ]; then . '/Users/lgfolder/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/lgfolder/google-cloud-sdk/completion.zsh.inc' ]; then . '/Users/lgfolder/google-cloud-sdk/completion.zsh.inc'; fi

export PATH="/Users/lgfolder/google-cloud-sdk/bin/gcloud:$PATH"




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
