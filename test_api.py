import replicate

input = {
    # "local_source": "https://replicate.delivery/pbxt/KgRH3TXuSLGMGuRicUX9pKchG17Nk6qbJMzv6s0NvTj2nD7P/src.jpg",
    # "local_target": "https://replicate.delivery/pbxt/KgRH4AoijNe7h1lU84m4YwghJNdZ520I7qhGe0ip1ufa9CSA/tgt.jpg"
'local_source': 'http://localhost:5000/static/images/Thanh_photo.jpg', 
'local_target': 'http://localhost:5000/static/images/photo4.png'
}

output = replicate.run(
    "xiankgx/face-swap:cff87316e31787df12002c9e20a78a017a36cb31fde9862d8dedd15ab29b7288",
    input=input
)
print(output)
#=> {"msg":"succeed","code":200,"image":"https://storage.goog...