```
git tag -l | xargs -n 1 git push --delete origin
git tag -l | xargs git tag -d
```

```
git tag v1                                      
git push origin v1
```