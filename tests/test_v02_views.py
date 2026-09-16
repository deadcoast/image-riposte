import io
import numpy as np
import pytest
from PIL import Image
from riposte.errors import RiposteError
from riposte.views import (TRAIN_VIEWS,HOLDOUT_VIEWS,publication_view,image_tensor,tensor_image,
                           differentiable_view,keep_mask,budget_map,spectral_direction,matched_control)
torch=pytest.importorskip('torch')
torch.set_num_threads(1)

def fixture_image(size=(25,19)):
    a=np.random.default_rng(91).integers(0,256,(size[1],size[0],3),dtype=np.uint8)
    return Image.fromarray(a)

@pytest.mark.parametrize('view',TRAIN_VIEWS+HOLDOUT_VIEWS)
def test_true_views_deterministic(view):
    im=fixture_image();a=publication_view(im,view);b=publication_view(im,view)
    assert a.mode=='RGB' and a.tobytes()==b.tobytes()
    assert not a.info

@pytest.mark.parametrize('view',TRAIN_VIEWS)
def test_backward_proxy_forward_matches_published_8bit_pixels(view):
    x=image_tensor(fixture_image()).requires_grad_()
    y=differentiable_view(x,view)
    actual=image_tensor(publication_view(tensor_image(x),view))
    # Floating arithmetic is not a bitstream, but re-encoded 8-bit samples must match exactly.
    assert torch.equal((y*255).round(),(actual*255).round())
    y.square().mean().backward()
    assert x.grad is not None and torch.isfinite(x.grad).all() and (x.grad!=0).any()

@pytest.mark.parametrize('q',[70,60,85])
def test_jpeg_matches_pillow_420(q):
    image=fixture_image();stream=io.BytesIO();image.save(stream,'JPEG',quality=q,subsampling=2,optimize=False)
    stream.seek(0)
    with Image.open(stream) as value:
        assert publication_view(image,'jpeg'+str(q)).tobytes()==value.convert('RGB').tobytes()

@pytest.mark.parametrize('kind',['whole','center','left','right','top','bottom'])
def test_keep_masks_binary_reproducible(kind):
    a=keep_mask((23,29),kind,31);b=keep_mask((23,29),kind,31)
    assert torch.equal(a,b) and set(a.unique().tolist())<= {0.,1.}
    assert (a==0).any() if kind!='whole' else bool((a==1).all())
    if kind=='right':assert bool((a[:,:,:,-1]==0).any())
    if kind=='bottom':assert bool((a[:,:,-1,:]==0).any())

@pytest.mark.parametrize('size',[(19,21),(32,32),(8,16)])
def test_spectral_search_shape_and_finite(size):
    x=torch.randn(1,3,*size)
    assert torch.equal(spectral_direction(x,0),x)
    y=spectral_direction(x,.65)
    assert y.shape==x.shape and torch.isfinite(y).all()

@pytest.mark.parametrize('epsilon',[1,4,8,16])
def test_budget_integer_and_preserves_white(epsilon):
    x=torch.ones(1,3,32,32);x[:,:,12:20,12:20]=0
    b=budget_map(x,epsilon)
    assert (b*255).equal((b*255).round()) and b.max()<=epsilon/255
    assert b[0,0,2,2]==0 and b[0,0,15,15]==epsilon/255

@pytest.mark.parametrize('seed',[0,7,101,211,2**32-1])
def test_control_exact_absolute_difference_with_boundary_pixels(seed):
    a=np.array([[[0,255,1],[254,70,120]],[[0,255,180],[13,244,240]]],dtype=np.uint8)
    b=np.array([[[255,0,201],[30,90,100]],[[12,233,201],[21,222,255]]],dtype=np.uint8)
    result=np.asarray(matched_control(Image.fromarray(a),Image.fromarray(b),seed),dtype=np.int16)
    assert np.array_equal(np.abs(result-a.astype(np.int16)),np.abs(b.astype(np.int16)-a.astype(np.int16)))
    assert result.min()>=0 and result.max()<=255

@pytest.mark.parametrize('epsilon',[0,17,-1,True,2.5])
def test_invalid_budget(epsilon):
    with pytest.raises(RiposteError):budget_map(torch.ones(1,3,20,20),epsilon)

def test_sign_controls_differ_and_unchanged_zero():
    a=Image.new('RGB',(32,32),(100,100,100));b=Image.new('RGB',a.size,(104,104,104))
    assert matched_control(a,b,101).tobytes()!=matched_control(a,b,211).tobytes()
    assert matched_control(a,a,101).tobytes()==a.tobytes()

def test_unknown_views_and_masks_rejected():
    with pytest.raises(RiposteError):publication_view(fixture_image(),'imaginary-platform')
    with pytest.raises(RiposteError):keep_mask((20,20),'unknown')
    with pytest.raises(RiposteError):differentiable_view(image_tensor(fixture_image()),'jpeg70')
